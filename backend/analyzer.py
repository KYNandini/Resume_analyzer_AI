"""
Resume Analyzer - Advanced Skill Extraction & Matching Engine
=============================================================
Model stack:
  - spaCy en_core_web_lg  → NER + noun-chunk phrase extraction
  - all-MiniLM-L6-v2      → Fast semantic similarity (80 MB, offline after first run)
  - Curated TECH_SKILLS   → 700+ skills vocabulary with categories
  - Google Gemini API     → Context-aware AI improvement suggestions
"""

import re
import os
import sys
import json
from typing import Optional
from dotenv import load_dotenv

# Cloud APIs removed for offline functionality

# ---------------------------------------------------------------------------
# SBERT model name — small but highly accurate for skill matching
# Downloads once (~80 MB) then cached locally at:
#   Windows: C:\Users\<user>\.cache\huggingface\hub\
# After first download works 100% offline
# ---------------------------------------------------------------------------
SBERT_MODEL_NAME = "all-MiniLM-L6-v2"

# Optional heavy NLP deps — gracefully degrade on Python 3.14+
try:
    import spacy
    _SPACY_AVAILABLE = True
except Exception:
    spacy = None
    _SPACY_AVAILABLE = False
    print("[analyzer] spaCy not available — using regex-only skill extraction (Pass 1 only)", file=sys.stderr)

try:
    from sentence_transformers import SentenceTransformer, util as sbert_util
    _SBERT_AVAILABLE = True
except Exception:
    SentenceTransformer = None
    sbert_util = None
    _SBERT_AVAILABLE = False
    print("[analyzer] sentence-transformers not available — using exact-match only", file=sys.stderr)

load_dotenv()

# ---------------------------------------------------------------------------
# Models — pre-warmed at import time so first request is instant
# ---------------------------------------------------------------------------
_nlp = None
_sbert = None

def get_nlp():
    global _nlp
    if not _SPACY_AVAILABLE:
        return None
    if _nlp is None:
        try:
            _nlp = spacy.load("en_core_web_lg")
        except OSError:
            try:
                _nlp = spacy.load("en_core_web_sm")
            except OSError:
                _nlp = None
                print("[analyzer] No spaCy model found. Run: python -m spacy download en_core_web_sm", file=sys.stderr)
    return _nlp

def get_sbert():
    """Load SBERT model from local cache — downloads automatically on first run."""
    global _sbert
    if not _SBERT_AVAILABLE:
        return None
    if _sbert is None:
        try:
            print(f"[analyzer] Loading SBERT model '{SBERT_MODEL_NAME}' (from cache or downloading)...", file=sys.stderr)
            _sbert = SentenceTransformer(SBERT_MODEL_NAME)
            print(f"[analyzer] SBERT model ready ✓", file=sys.stderr)
        except Exception as e:
            print(f"[analyzer] SBERT model load failed: {e} — falling back to exact-match", file=sys.stderr)
            _sbert = None
    return _sbert

# Pre-warm SBERT model at import time so it's ready for the first request
if _SBERT_AVAILABLE:
    try:
        get_sbert()
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Curated Tech Skills Vocabulary  (skill_normalized -> category)
# ---------------------------------------------------------------------------
TECH_SKILLS: dict[str, str] = {
    # ── Programming Languages ──
    "python": "Programming", "java": "Programming", "javascript": "Programming",
    "typescript": "Programming", "c++": "Programming", "c#": "Programming",
    "c": "Programming", "go": "Programming", "golang": "Programming",
    "rust": "Programming", "kotlin": "Programming", "swift": "Programming",
    "r": "Programming", "scala": "Programming", "ruby": "Programming",
    "php": "Programming", "perl": "Programming", "matlab": "Programming",
    "bash": "Programming", "shell scripting": "Programming", "powershell": "Programming",
    "dart": "Programming", "lua": "Programming", "julia": "Programming",

    # ── Web & Frontend ──
    "react": "Frontend", "reactjs": "Frontend", "react.js": "Frontend",
    "angular": "Frontend", "angularjs": "Frontend",
    "vue": "Frontend", "vuejs": "Frontend", "vue.js": "Frontend",
    "nextjs": "Frontend", "next.js": "Frontend",
    "nuxt": "Frontend", "svelte": "Frontend",
    "html": "Frontend", "html5": "Frontend",
    "css": "Frontend", "css3": "Frontend", "sass": "Frontend", "scss": "Frontend",
    "tailwind": "Frontend", "tailwindcss": "Frontend", "bootstrap": "Frontend",
    "webpack": "Frontend", "vite": "Frontend", "parcel": "Frontend",
    "redux": "Frontend", "mobx": "Frontend", "graphql": "Frontend",
    "rest api": "Frontend", "restful api": "Frontend", "rest": "Frontend",
    "ajax": "Frontend", "jquery": "Frontend",

    # ── Backend & Frameworks ──
    "nodejs": "Backend", "node.js": "Backend", "node": "Backend",
    "django": "Backend", "flask": "Backend", "fastapi": "Backend",
    "spring boot": "Backend", "spring": "Backend", "express": "Backend",
    "expressjs": "Backend", "rails": "Backend", "ruby on rails": "Backend",
    "laravel": "Backend", "asp.net": "Backend", "dotnet": "Backend",
    "microservices": "Backend", "grpc": "Backend", "websocket": "Backend",
    "graphql": "Backend", "kafka": "Backend", "rabbitmq": "Backend",
    "celery": "Backend", "redis": "Backend", "nginx": "Backend",
    "apache": "Backend",

    # ── Databases ──
    "sql": "Database", "mysql": "Database", "postgresql": "Database",
    "postgres": "Database", "sqlite": "Database", "oracle": "Database",
    "mongodb": "Database", "mongoose": "Database", "cassandra": "Database",
    "dynamodb": "Database", "firebase": "Database", "firestore": "Database",
    "redis": "Database", "elasticsearch": "Database", "neo4j": "Database",
    "snowflake": "Database", "bigquery": "Database", "supabase": "Database",

    # ── Cloud & DevOps ──
    "aws": "Cloud", "amazon web services": "Cloud", "gcp": "Cloud",
    "google cloud": "Cloud", "azure": "Cloud", "microsoft azure": "Cloud",
    "docker": "DevOps", "kubernetes": "DevOps", "k8s": "DevOps",
    "terraform": "DevOps", "ansible": "DevOps", "helm": "DevOps",
    "jenkins": "DevOps", "github actions": "DevOps", "gitlab ci": "DevOps",
    "circleci": "DevOps", "ci/cd": "DevOps", "devops": "DevOps",
    "linux": "DevOps", "unix": "DevOps", "git": "Tools",
    "prometheus": "DevOps", "grafana": "DevOps", "datadog": "DevOps",
    "serverless": "Cloud", "lambda": "Cloud", "ec2": "Cloud",
    "s3": "Cloud", "cloudformation": "Cloud",

    # ── AI / ML / Data Science ──
    "machine learning": "AI/ML", "ml": "AI/ML", "deep learning": "AI/ML",
    "neural network": "AI/ML", "artificial intelligence": "AI/ML", "ai": "AI/ML",
    "nlp": "AI/ML", "natural language processing": "AI/ML",
    "computer vision": "AI/ML", "cv": "AI/ML",
    "tensorflow": "AI/ML", "pytorch": "AI/ML", "keras": "AI/ML",
    "scikit-learn": "AI/ML", "sklearn": "AI/ML",
    "hugging face": "AI/ML", "transformers": "AI/ML",
    "langchain": "AI/ML", "llm": "AI/ML", "large language model": "AI/ML",
    "openai": "AI/ML", "gpt": "AI/ML", "bert": "AI/ML",
    "xgboost": "AI/ML", "lightgbm": "AI/ML", "random forest": "AI/ML",
    "data science": "AI/ML", "data analysis": "AI/ML",
    "pandas": "AI/ML", "numpy": "AI/ML", "matplotlib": "AI/ML",
    "seaborn": "AI/ML", "plotly": "AI/ML", "scipy": "AI/ML",

    # ── Data Engineering ──
    "spark": "Data Engineering", "apache spark": "Data Engineering",
    "hadoop": "Data Engineering", "hive": "Data Engineering",
    "airflow": "Data Engineering", "dbt": "Data Engineering",
    "etl": "Data Engineering", "data pipeline": "Data Engineering",
    "data warehouse": "Data Engineering", "data lake": "Data Engineering",
    "tableau": "Data Engineering", "power bi": "Data Engineering",
    "looker": "Data Engineering",

    # ── Mobile ──
    "android": "Mobile", "ios": "Mobile", "react native": "Mobile",
    "flutter": "Mobile", "swift": "Mobile", "kotlin": "Mobile",
    "xamarin": "Mobile",

    # ── Testing & QA ──
    "selenium": "Testing", "cypress": "Testing", "jest": "Testing",
    "pytest": "Testing", "unittest": "Testing", "mocha": "Testing",
    "junit": "Testing", "testng": "Testing", "playwright": "Testing",
    "postman": "Tools", "tdd": "Testing", "bdd": "Testing",
    "unit testing": "Testing", "integration testing": "Testing",

    # ── Finance & Accounting ──
    "accountancy": "Finance", "accounting": "Finance", "financial accounting": "Finance",
    "management accounting": "Finance", "cost accounting": "Finance", "corporate finance": "Finance",
    "bookkeeping": "Finance", "auditing": "Finance", "audit": "Finance", "internal audit": "Finance",
    "financial audit": "Finance", "taxation": "Finance", "tax planning": "Finance",
    "income tax": "Finance", "gst": "Finance", "vat": "Finance", "tally": "Finance",
    "tally prime": "Finance", "quickbooks": "Finance", "sap fico": "Finance",
    "financial modeling": "Finance", "financial reporting": "Finance", "financial analysis": "Finance",
    "accounts payable": "Finance", "accounts receivable": "Finance", "payroll": "Finance",
    "bank reconciliation": "Finance", "reconciliation": "Finance", "balance sheet": "Finance",
    "cash flow": "Finance", "budgeting": "Finance", "financial forecasting": "Finance",
    "cpa": "Finance", "acca": "Finance", "chartered accountancy": "Finance",
    "compliance": "Finance", "risk management": "Finance", "banking": "Finance",
    "credit analysis": "Finance", "financial planning": "Finance", "tally erp": "Finance",

    # ── Security ──
    "cybersecurity": "Security", "penetration testing": "Security",
    "ethical hacking": "Security", "owasp": "Security",
    "ssl": "Security", "tls": "Security", "oauth": "Security",
    "jwt": "Security", "encryption": "Security",

    # ── Soft Skills ──
    "leadership": "Soft Skills", "communication": "Soft Skills",
    "teamwork": "Soft Skills", "problem solving": "Soft Skills",
    "critical thinking": "Soft Skills", "time management": "Soft Skills",
    "project management": "Soft Skills", "agile": "Soft Skills",
    "scrum": "Soft Skills", "kanban": "Soft Skills", "jira": "Soft Skills",
    "collaboration": "Soft Skills", "adaptability": "Soft Skills",
    "creativity": "Soft Skills", "analytical": "Soft Skills",

    # ── Tools ──
    "linux": "Tools", "windows": "Tools", "macos": "Tools",
    "vscode": "Tools", "intellij": "Tools", "eclipse": "Tools",
    "github": "Tools", "gitlab": "Tools", "bitbucket": "Tools",
    "confluence": "Tools", "notion": "Tools", "figma": "Tools",
    "photoshop": "Tools", "excel": "Tools", "powerpoint": "Tools",
    "hadoop": "Tools", "kafka": "Tools",

    # ── Business & Management ──
    "business analysis": "Business & Management", "requirements gathering": "Business & Management",
    "stakeholder management": "Business & Management", "gap analysis": "Business & Management",
    "process improvement": "Business & Management", "swot analysis": "Business & Management",
    "feasibility study": "Business & Management", "kpis": "Business & Management",
    "kpi": "Business & Management", "business process": "Business & Management",

    # ── HR & People Operations ──
    "recruitment": "HR & Operations", "talent acquisition": "HR & Operations",
    "human resources": "HR & Operations", "hr": "HR & Operations",
    "sourcing": "HR & Operations", "screening": "HR & Operations",
    "interviewing": "HR & Operations", "employee onboarding": "HR & Operations",
    "onboarding": "HR & Operations", "employee engagement": "HR & Operations",
    "hr policies": "HR & Operations", "payroll administration": "HR & Operations",
    "performance management": "HR & Operations", "employee relations": "HR & Operations",
    "ats": "HR & Operations",

    # ── Marketing & Growth ──
    "digital marketing": "Marketing & Growth", "seo": "Marketing & Growth",
    "sem": "Marketing & Growth", "social media marketing": "Marketing & Growth",
    "content marketing": "Marketing & Growth", "content writing": "Marketing & Growth",
    "copywriting": "Marketing & Growth", "email marketing": "Marketing & Growth",
    "google analytics": "Marketing & Growth", "campaign management": "Marketing & Growth",
    "lead generation": "Marketing & Growth", "crm": "Marketing & Growth",
    "hubspot": "Marketing & Growth", "branding": "Marketing & Growth",

    # ── Core Engineering & Embedded ──
    "embedded systems": "Core Engineering", "embedded": "Core Engineering",
    "microcontrollers": "Core Engineering", "arduino": "Core Engineering",
    "raspberry pi": "Core Engineering", "iot": "Core Engineering",
    "circuit design": "Core Engineering", "pcb design": "Core Engineering",
    "vlsi": "Core Engineering", "verilog": "Core Engineering",
    "vhdl": "Core Engineering", "plc": "Core Engineering",
    "scada": "Core Engineering", "power systems": "Core Engineering",
    "renewable energy": "Core Engineering", "sensors": "Core Engineering",
    "cad": "Core Engineering", "autocad": "Core Engineering",
    "solidworks": "Core Engineering", "ansys": "Core Engineering",

    # ── Architecture & Design ──
    "system design": "Architecture", "api design": "Architecture",
    "oop": "Architecture", "object oriented": "Architecture",
    "functional programming": "Architecture", "design patterns": "Architecture",
    "solid principles": "Architecture", "clean architecture": "Architecture",
    "mvc": "Architecture", "mvvm": "Architecture",
    "distributed systems": "Architecture",
}

# Normalisation aliases (common abbreviations → canonical form)
ALIASES: dict[str, str] = {
    "reactjs": "react", "react.js": "react",
    "vuejs": "vue", "vue.js": "vue",
    "nodejs": "node.js", "node": "node.js",
    "nextjs": "next.js",
    "pg": "postgresql", "postgres": "postgresql",
    "mongo": "mongodb",
    "sklearn": "scikit-learn",
    "ml": "machine learning",
    "ai": "artificial intelligence",
    "nlp": "natural language processing",
    "dl": "deep learning",
    "k8s": "kubernetes",
    "tf": "tensorflow",
    "gcp": "google cloud",
    "devops": "devops",
    "ci/cd": "ci/cd",
    "js": "javascript",
    "ts": "typescript",
    "express": "express.js",
    "expressjs": "express.js",
    "rest": "rest apis",
    "rest api": "rest apis",
    "restful api": "rest apis",
    "oop": "oop",
    "object-oriented programming": "oop",
    "object oriented programming": "oop",
    "dsa": "data structures & algorithms",
    "data structures": "data structures",
    "algorithms": "algorithms",
    "dbms": "dbms",
    "operating systems": "operating systems",
    "computer networks": "computer networks",
    "data science": "data science",
    "communication skills": "communication",
    "accountant": "accountancy",
    "accounting": "accountancy",
    "financial accountant": "financial accounting",
    "tally erp 9": "tally erp",
}

# Skills that are also common English words or single letters.
# These require case-sensitive matching to avoid false positives 
# (e.g., matching the letter 'c' in a bulleted list or the word 'go' in a sentence).
AMBIGUOUS_SKILLS: set[str] = {
    "c", "r", "go", "rest", "express", "spring", "ruby", "bash", "testing"
}

CIRCUMFERENCE = 2 * 3.14159 * 34


# ---------------------------------------------------------------------------
# Text normalisation
# ---------------------------------------------------------------------------
def normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s.#+/-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return ALIASES.get(text, text)


# ---------------------------------------------------------------------------
# Skill Extraction (two-pass: curated vocab lookup + NLP phrase extraction)
# ---------------------------------------------------------------------------
def extract_skills(text: str) -> list[dict]:
    """
    Returns list of dicts: {skill, category}
    Pass 1: Scan full text for all curated TECH_SKILLS phrases (sorted longest first
            to prevent 'react' matching before 'react native')
    Pass 2: spaCy noun chunks + named entities as fallback candidates (if spaCy available)
    """
    text_lower = text.lower()
    found: dict[str, str] = {}  # skill -> category

    # ── Pass 1: Curated vocabulary scan (phrase-aware, longest match first) ──
    sorted_skills = sorted(TECH_SKILLS.keys(), key=len, reverse=True)
    for skill in sorted_skills:
        canonical = ALIASES.get(skill, skill)
        if canonical in found:
            continue

        # Prevent partial matches inside words, but allow dots/pluses for things like c++ or node.js
        start_bound = r"(?<![a-zA-Z0-9+#-])"
        end_bound = r"(?![a-zA-Z0-9+#-])"
        
        if skill in AMBIGUOUS_SKILLS:
            # Case sensitive match required for ambiguous skills
            if len(skill) == 1:
                valid_cases = [skill.upper()]
            else:
                valid_cases = [skill.title(), skill.upper()]
                
            cases_pattern = "|".join(re.escape(c) for c in valid_cases)
            pattern = start_bound + r"(?:" + cases_pattern + r")" + end_bound
            
            if re.search(pattern, text):
                found[canonical] = TECH_SKILLS.get(canonical, TECH_SKILLS.get(skill, "General"))
        else:
            # Case insensitive match for normal skills
            pattern = start_bound + re.escape(skill) + end_bound
            if re.search(pattern, text_lower):
                found[canonical] = TECH_SKILLS.get(canonical, TECH_SKILLS.get(skill, "General"))

    # ── Pass 2: spaCy noun chunks + NER as supplementary extraction ──
    nlp = get_nlp()
    if nlp is not None:
        doc = nlp(text[:50000])  # cap for speed

        for chunk in doc.noun_chunks:
            phrase = normalize(chunk.text)
            if len(phrase) > 1 and phrase in TECH_SKILLS and phrase not in found:
                if phrase not in AMBIGUOUS_SKILLS:
                    found[phrase] = TECH_SKILLS[phrase]

        for ent in doc.ents:
            if ent.label_ in {"PRODUCT", "ORG", "GPE", "WORK_OF_ART"}:
                phrase = normalize(ent.text)
                if phrase in TECH_SKILLS and phrase not in found:
                    if phrase not in AMBIGUOUS_SKILLS:
                        found[phrase] = TECH_SKILLS[phrase]

    return [{"skill": k, "category": v} for k, v in found.items()]


# ---------------------------------------------------------------------------
# Semantic Matching Engine
# ---------------------------------------------------------------------------
def _simple_similarity(a: str, b: str) -> float:
    """Character-level Jaccard similarity as fallback when SBERT unavailable."""
    set_a = set(a.lower().split())
    set_b = set(b.lower().split())
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def match_skills(
    resume_skills: list[dict],
    job_skills: list[dict],
    threshold: float = 0.72,
) -> dict:
    """
    Two-pass matching:
      1. Exact match (normalized skill name)
      2. Semantic similarity via all-mpnet-base-v2 (or simple Jaccard fallback)
    
    Returns: {matched, missing, matchPercent, missingPercent, efficiencyPercent, ...}
    """
    if not job_skills:
        return _empty_result()

    sbert = get_sbert()

    resume_names = [s["skill"] for s in resume_skills]
    job_names    = [s["skill"] for s in job_skills]

    # Deduplicate
    resume_names = list(dict.fromkeys(resume_names))
    job_names    = list(dict.fromkeys(job_names))

    if not resume_names:
        return _empty_result(job_skills)

    resume_set = set(resume_names)
    matched_skills: list[dict] = []
    missing_skills: list[dict] = []

    job_skill_map = {s["skill"]: s["category"] for s in job_skills}

    # Pre-encode with SBERT if available
    if sbert is not None:
        resume_embeddings = sbert.encode(resume_names, convert_to_tensor=True, normalize_embeddings=True)
        job_embeddings    = sbert.encode(job_names,    convert_to_tensor=True, normalize_embeddings=True)

    for i, job_name in enumerate(job_names):
        category = job_skill_map.get(job_name, "General")

        # Pass 1: Exact match
        if job_name in resume_set:
            matched_skills.append({
                "skill": job_name,
                "category": category,
                "confidence": 100,
                "matchType": "exact"
            })
            continue

        # Pass 2: Semantic similarity (SBERT) or Jaccard fallback
        if sbert is not None:
            scores = sbert_util.cos_sim(job_embeddings[i], resume_embeddings)[0]
            best_score = float(scores.max())
            best_idx   = int(scores.argmax())
        else:
            sims = [_simple_similarity(job_name, r) for r in resume_names]
            best_score = max(sims) if sims else 0.0
            best_idx   = sims.index(best_score) if sims else 0
            threshold  = 0.3  # lower bar for Jaccard

        if best_score >= threshold:
            matched_skills.append({
                "skill": job_name,
                "category": category,
                "confidence": round(best_score * 100),
                "matchedWith": resume_names[best_idx],
                "matchType": "semantic"
            })
        else:
            # Priority: skills with low confidence get higher fix priority
            priority = "High" if best_score < 0.4 else "Medium"
            missing_skills.append({
                "skill": job_name,
                "category": category,
                "priority": priority,
                "closestMatch": resume_names[best_idx] if best_score > 0.25 else None,
                "similarity": round(best_score * 100)
            })

    total = len(job_names)
    match_count = len(matched_skills)
    match_pct = round((match_count / total) * 100) if total else 0
    # Cap at 97% — a perfect 100% ATS score is not realistic
    match_pct = min(match_pct, 97)
    missing_pct = 100 - match_pct
    eff_pct = min(match_pct + 8, 97)

    # Category breakdown
    category_stats: dict[str, dict] = {}
    for s in job_skills:
        cat = s["category"]
        if cat not in category_stats:
            category_stats[cat] = {"total": 0, "matched": 0}
        category_stats[cat]["total"] += 1

    for s in matched_skills:
        cat = s["category"]
        if cat in category_stats:
            category_stats[cat]["matched"] += 1

    return {
        "matchPercent": match_pct,
        "missingPercent": missing_pct,
        "efficiencyPercent": eff_pct,
        "matchingSkills": matched_skills,
        "missingSkills": missing_skills,
        "totalSkills": total,
        "matchedCount": match_count,
        "categoryBreakdown": category_stats,
    }


def _empty_result(job_skills: list[dict] = None) -> dict:
    missing = job_skills if job_skills else []
    for s in missing:
        s.setdefault("priority", "High")
        s.setdefault("similarity", 0)
    return {
        "matchPercent": 0,
        "missingPercent": 100,
        "efficiencyPercent": 10,
        "matchingSkills": [],
        "missingSkills": missing,
        "totalSkills": len(missing),
        "matchedCount": 0,
        "categoryBreakdown": {},
    }


# ---------------------------------------------------------------------------
# Offline AI Suggestions
# ---------------------------------------------------------------------------
def get_gemini_suggestions(missing_skills: list[dict], job_context: str) -> dict[str, str]:
    """
    Offline implementation: Generate improvement suggestions using static fallbacks.
    """
    if not missing_skills:
        return {}

    all_skill_names = [s["skill"] for s in missing_skills]
    suggestions = {}

    for skill in all_skill_names:
        suggestions[skill.lower()] = _static_suggestion(skill)

    return suggestions


def _static_suggestion(skill: str) -> str:
    s = skill.lower()
    category = TECH_SKILLS.get(s, "General")

    if category == "AI/ML":
        return f"Take a hands-on course on {skill} (Coursera/Fast.ai) and build a small project to showcase on GitHub."
    if category == "Cloud":
        return f"Earn the entry-level {skill} certification — it's highly valued and beginner-friendly."
    if category == "DevOps":
        return f"Set up a personal CI/CD pipeline using {skill} on a side project to gain practical experience."
    if category == "Frontend":
        return f"Build a small portfolio project using {skill} and deploy it to Vercel or Netlify."
    if category == "Backend":
        return f"Create a REST API using {skill} in a personal project and document it with Swagger/OpenAPI."
    if category == "Database":
        return f"Practice {skill} through LeetCode SQL problems or design a schema for a real-world use case."
    if category == "Programming":
        return f"Complete 20+ {skill} exercises on LeetCode or HackerRank and add {skill} projects to your GitHub."
    if category == "Soft Skills":
        return f"Highlight {skill} in your experience bullets — use the STAR method (Situation, Task, Action, Result)."
    if category == "Testing":
        return f"Add automated tests using {skill} to an existing project to demonstrate quality assurance skills."
    if category == "Finance":
        return f"Highlight your {skill} knowledge by listing relevant certifications (e.g., ACCA, CPA) and quantify financial outcomes in your experience bullets."
    if category == "Security":
        return f"Earn a foundational {skill} certification (e.g., CompTIA Security+) and set up a home lab to practice defensive techniques."
    if category == "Architecture":
        return f"Document system design decisions using {skill} principles in your portfolio — draw architecture diagrams and explain trade-offs."
    if category == "Mobile":
        return f"Build and publish a small mobile app using {skill} to the Play Store or App Store to demonstrate hands-on experience."
    return f"Research {skill} through official documentation and build a demo project showcasing its core features."


def _is_summary_or_non_edu(line: str) -> bool:
    """Detect sentences that describe summaries, objectives, skills, projects, declarations, or personal details."""
    l = line.lower().strip()
    if not l:
        return True
    
    summary_indicators = [
        "dedicated", "motivated", "seeking", "looking for", "aspiring", "passionate",
        "to work in", "to secure", "to obtain", "to serve", "eager to", "enthusiastic",
        "career objective", "professional summary", "about me", "profile summary",
        "results-driven", "hard-working", "strong foundation in", "proficient in",
        "hands-on experience", "proven track record", "self-motivated", "dynamic professional",
        "willing to work", "contribute to", "strive for", "aim to", "responsible for",
        "skilled in using", "experience in hands-on", "experience in", "worked on",
        "projects involving", "simulation and analysis", "circuit design", "power systems",
        "microcontrollers", "embedded systems", "software tools such as",
        "i hereby declare", "i certify that", "true and accurate", "to the best of my knowledge",
        "date of birth", "gender:", "father's name", "permanent address", "hobbies:",
        "languages known", "declaration", "place:", "date:"
    ]
    if any(ind in l for ind in summary_indicators):
        if not re.match(r'^(?:b\.?e\.?|b\.?tech|bachelor|master|m\.?tech|diploma|sslc|puc)', l):
            return True
        if len(l.split()) > 7:
            return True

    # Coursework or project lines
    if re.match(r'^(?:relevant\s+)?(?:courses|coursework|subjects|electives|modules)[\s:-]', l):
        return True
    if re.match(r'^(?:projects?|key\s+projects?|responsibilities|achievements?)[\s:-]', l):
        return True
    if re.match(r'^(?:skills?|technical\s+skills?|tools?)[\s:-]', l):
        return True
        
    return False


def _is_edu_header_line(line: str) -> bool:
    # A line with a graduation year, percentage, or CGPA is NEVER a table header!
    if re.search(r'\b(19|20)\d{2}\b', line) or '%' in line or re.search(r'\b(?:cgpa|gpa)[\s:-]*\d\b', line, re.IGNORECASE):
        return False
        
    l = line.lower().strip()
    l = re.sub(r'^[|\s\-#*:]+', '', l)
    l = re.sub(r'[|\s\-#*:]+$', '', l)
    
    header_kws = [
        "institution", "university", "college", "school", "passing", 
        "cgpa", "percentile", "percentage", "marks", "grade", "degree", 
        "course", "qualification", "board", "stream", "specialization", 
        "duration", "batch", "score"
    ]
    kw_hits = sum(1 for kw in header_kws if kw in l)
    
    if ('|' in line or '\t' in line) and kw_hits >= 2:
        return True
    return kw_hits >= 3 or ("degree" in l and "institution" in l) or ("course" in l and "college" in l) or ("institution" in l and "passing" in l)


DEGREE_PATTERNS = [
    # Doctorates
    r'\b(?:ph\.?d|doctorate|doctor\s+of\s+(?:philosophy|science)|d\.phil)\b',
    # Masters
    r'\b(?:m\.?tech|m\.?e\.?|(?<![a-z]\.)m\.s\.|(?<![a-z]\.)ms\b|m\.?sc|mca|mba|m\.?com|m\.?a\.|m\.?des|pg\s+diploma|post\s+graduate\s+diploma)\b',
    r'\b(?:master(?:\'?s)?\s+of\s+(?:technology|engineering|science|arts|commerce|business\s+administration|computer\s+applications|philosophy|design|architecture|pharmacy|education))\b',
    r'\bmaster(?:\'?s)?\s+degree\b',
    # Bachelors & Engineering
    r'\b(?:b\.?tech|b\.?e\.?|(?<![a-z]\.)b\.s\.|(?<![a-z]\.)bs\b|b\.?sc|bca|bba|b\.?com|b\.?a\.|b\.?des|b\.?arch|mbbs)\b',
    r'\b(?:bachelor(?:\'?s)?\s+of\s+(?:technology|engineering|science|arts|commerce|business\s+administration|computer\s+applications|philosophy|design|architecture|pharmacy|education|laws))\b',
    r'\bbachelor(?:\'?s)?\s+degree\b',
    # Engineering branches without explicit B.E./B.Tech prefix
    r'\b(?:computer\s+science(?:\s+(?:and|&)\s+engineering)?|information\s+(?:science|technology)(?:\s+(?:and|&)\s+engineering)?|electrical(?:\s+(?:and|&)\s+electronics)?(?:\s+engineering)?|electronics(?:\s+(?:and|&)\s+communication)?(?:\s+engineering)?|(?:mechanical|civil|chemical|biotechnology|aeronautical|automobile|aerospace|industrial|robotics|data\s+science)\s+engineering)\b',
    # Diploma
    r'\b(?:diploma(?:\s+in\s+[A-Za-z\s&]+)?|polytechnic(?:\s+diploma)?|advanced\s+diploma)\b',
    # Pre-University / 12th
    r'\b(?:pre[- ]university(?:\s+course)?|puc(?:\s*-\s*[a-z]+)?|higher\s+secondary(?:\s+education)?|senior\s+secondary(?:\s+education)?|intermediate(?:\s*\(?[a-z]+\)?)?|12th(?:\s+std|\s+standard|\s+grade)?|class\s+(?:xii|12|12th)|hsc|plus\s+two|\+2)\b',
    # Secondary / 10th
    r'\b(?:secondary\s+school\s+leaving\s+certificate|secondary\s+education|secondary\s+school|sslc|10th(?:\s+std|\s+standard|\s+grade)?|class\s+(?:x|10|10th)|matriculation|high\s+school\s+(?:certificate|diploma))\b',
    # Associate
    r'\b(?:associate(?:\'?s)?\s+degree)\b'
]

INST_PATTERNS = [
    r'\b(?:college|pu\s+college)\b',
    r'(?<!pre[- ])\buniversity\b',
    r'\b(?:institute|institution|academy|vidyalaya|polytechnic|campus|vtu|iit|nit|iisc|bits|mit)\b',
    r'(?<!secondary\s)(?<!senior\s)(?<!higher\s)\bschool\b',
    r'\b(?:board|council|examination\s+board)\b',
    r'\b(?:society|trust|samiti|sanstha|mandal|kendra|bhavan|vidyapeeth(?:a)?|shikshan(?:a)?|sangh(?:a)?)\b',
    r'(?<!secondary\s)(?<!higher\s)(?<!technical\s)\beducation\b'
]


def _is_degree_kw(text: str) -> bool:
    t = text.lower()
    for pat in DEGREE_PATTERNS:
        if re.search(pat, t):
            return True
    return False


def _is_inst_kw(text: str) -> bool:
    t = text.lower()
    if re.search(r'\b(?:pre[- ]university\s+course|secondary\s+school\s+leaving\s+certificate|secondary\s+school|secondary\s+education|sslc|puc)\b', t):
        if not re.search(r'\b(?:pu\s+college|high\s+school|public\s+school|grammar\s+school|secondary\s+school\s+examination\s+board)\b', t):
            return False
    return any(re.search(pat, t) for pat in INST_PATTERNS)


def _clean_field(text: str) -> str:
    if not text:
        return ""
    cleaned = re.sub(r'^[\s\-_–—•·▪►|:,;~"\'*#\ufffd]+', '', text)
    cleaned = re.sub(r'[\s\-_–—•·▪►|:,;~"\'*#\ufffd]+$', '', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned.strip()


def _extract_year_field(text: str):
    """
    Extracts actual or explicitly expected passing year.
    Returns (year_str, remaining_text).
    Never invents or assumes graduation year without explicit text evidence.
    """
    # 1. Expected graduation: "Expected 2026", "2022 - 2026 (Expected)", "Expected: May 2025"
    m = re.search(r'(?:(?:19|20)\d{2}\s*[-–—]\s*)?(?:(?:19|20)\d{2})\s*\(?(?:Expected|Pursuing)\)?', text, re.IGNORECASE)
    if m:
        yr = _clean_field(m.group(0))
        rem = text.replace(m.group(0), ' ')
        return yr, rem

    m = re.search(r'(?:Expected|Graduating|Graduation)[\s:-]*(?:[A-Za-z]+\s+)?\b((?:19|20)\d{2})\b', text, re.IGNORECASE)
    if m:
        yr = f"{m.group(1)} (Expected)"
        rem = text.replace(m.group(0), ' ')
        return yr, rem

    # 2. Passing year explicit: "Passing Year: 2024", "Year of Passing: 2022", "Passed in 2021", "Batch: 2020 - 2024"
    m = re.search(r'(?:Passing\s+Year|Year\s+of\s+Passing|Graduated|Batch|Passed\s+in)[\s:-]*(?:[A-Za-z]+\s+)?\b((?:19|20)\d{2}(?:\s*[-–—]\s*(?:19|20)\d{2})?)\b', text, re.IGNORECASE)
    if m:
        yr = _clean_field(m.group(1))
        rem = text.replace(m.group(0), ' ')
        return yr, rem

    # 3. Year range: "2020 - 2024" or "August 2020 - May 2024"
    m = re.search(r'\b(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s,.]*)?((?:19|20)\d{2})\s*[-–—]\s*(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s,.]*)?((?:19|20)\d{2})\b', text, re.IGNORECASE)
    if m:
        yr = f"{m.group(1)} – {m.group(2)}"
        rem = text.replace(m.group(0), ' ')
        return yr, rem

    # 4. Ongoing without expected year: "2022 - Present", "2021 - Ongoing"
    m = re.search(r'(?:[A-Za-z]+\s+)?\b((?:19|20)\d{2})\b\s*[-–—]\s*(?:Present|Ongoing|Current)\b', text, re.IGNORECASE)
    if m:
        yr = "—"
        rem = text.replace(m.group(0), ' ')
        return yr, rem

    # 5. Standalone year: "2024", "2021"
    m = re.search(r'\b(19\d{2}|20\d{2})\b', text)
    if m:
        yr = m.group(1)
        rem = text.replace(m.group(0), ' ')
        return yr, rem

    return "", text


def _extract_grade_field(text: str):
    """
    Extracts percentage, CGPA, GPA, or grade.
    Returns (grade_str, remaining_text).
    Never converts CGPA to percentage or invents values.
    """
    # 1. CGPA: "CGPA: 8.8", "with a CGPA of 8.4", "8.8 CGPA", "CGPA 7.75 / 10"
    m = re.search(r'\b(?:with\s+a\s+)?CGPA(?:\s+of)?[\s:-]*([0-9]+(?:\.[0-9]+)?)(?:\s*/\s*(?:10(?:\.0+)?|4(?:\.0+)?|100))?\b', text, re.IGNORECASE)
    if m:
        score = m.group(1)
        rem = text.replace(m.group(0), ' ')
        return f"CGPA: {score}", rem
        
    m = re.search(r'\b([0-9]+(?:\.[0-9]+)?)\s*CGPA\b', text, re.IGNORECASE)
    if m:
        rem = text.replace(m.group(0), ' ')
        return f"CGPA: {m.group(1)}", rem

    # 2. GPA out of 4: "GPA: 3.8 / 4.0", "3.8 / 4.0 GPA", "3.85 / 4.0"
    m = re.search(r'\b(?:GPA[\s:-]*)?([0-9]+(?:\.[0-9]+)?)\s*/\s*4(?:\.0+)?(?:\s*GPA)?\b', text, re.IGNORECASE)
    if m:
        rem = text.replace(m.group(0), ' ')
        return f"{m.group(1)} / 4.0 GPA", rem

    # 3. Ratio out of 10: "7.75 / 10", "8.8 / 10"
    m = re.search(r'\b([0-9]+(?:\.[0-9]+)?)\s*/\s*10(?:\.0+)?\b', text)
    if m:
        rem = text.replace(m.group(0), ' ')
        return f"CGPA: {m.group(1)}", rem

    # 4. Percentage: "Percentage: 84.96%", "scoring 91.5%", "84.96%", "90.72%"
    m = re.search(r'(?:Percentage[\s:-]*|scoring[\s:-]*|with[\s:-]*)?([0-9]{1,3}(?:\.[0-9]+)?)\s*%', text, re.IGNORECASE)
    if m:
        rem = text.replace(m.group(0), ' ')
        return f"{m.group(1)}%", rem

    # 5. Percentile: "95.2 percentile"
    m = re.search(r'([0-9]{1,3}(?:\.[0-9]+)?)\s*(?:percentile|Percentile)\b', text)
    if m:
        rem = text.replace(m.group(0), ' ')
        return f"{m.group(1)} Percentile", rem

    return "", text


def _format_degree_name(degree: str) -> str:
    d = _clean_field(degree)
    if not d:
        return ""
    d = re.sub(r'^(?:Degree|Course|Qualification|Exam|Examination)[\s:-]+', '', d, flags=re.IGNORECASE)
    d = re.sub(r'^(?:percentage|cgpa|score)[\s:-]*[0-9]+(?:\.[0-9]+)?%?[\s,;:-]*', '', d, flags=re.IGNORECASE)
    d = re.sub(r'[,;\s]*(?:percentage|cgpa|score)[\s:-]*[0-9]+(?:\.[0-9]+)?%?.*$', '', d, flags=re.IGNORECASE)
    d = re.sub(r'[,;\s]*\b(19|20)\d{2}\b.*$', '', d)
    d = _clean_field(d)
    low = d.lower()
    
    # 12th / PUC normalization (checked first so class xii is not matched by class x)
    if any(k in low for k in ['pre-university', 'pre university', 'puc', 'pre-university course', 'pre university course']):
        return "Pre-University (PUC)"
    if re.search(r'\b(?:higher\s+secondary|12th|class\s+xii|class\s+12|hsc|plus\s+two|\+2|senior\s+secondary)\b', low):
        return "Higher Secondary (Class XII)"
    if 'intermediate' in low:
        return "Intermediate (Class XII)"

    # 10th / SSLC normalization
    if re.search(r'\b(?:secondary\s+education|secondary\s+school|sslc|10th|class\s+x|class\s+10|matriculation)\b', low):
        return "Secondary Education (SSLC)"
    if low in ['10th std / sslc', '10th std', '10th sslc', '10th standard / sslc', '10th std/sslc', 'class x (sslc)', 'class 10 (sslc)', 'secondary school (sslc)']:
        return "Class X (10th STD / SSLC)"

    # Engineering branches without B.E. / B.Tech prefix
    if re.search(r'\bengineering\b', low) and not any(k in low for k in ['b.e', 'b.tech', 'bachelor', 'master', 'm.tech', 'diploma']):
        return f"B.E. in {d}"

    return d


def _clean_inst_name(inst: str) -> str:
    cleaned = _clean_field(inst)
    if not cleaned:
        return ""
    cleaned = re.sub(r'^(?:Institution|Institute|University|College|School|Name\s+of\s+(?:the\s+)?(?:Institution|College|School|University))[\s]*[:\-]\s*', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'[,;\s]*(?:emphasizing|focusing|specializing|with)\s+core\s+subjects\s+.*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'[,;\s]*(?:emphasizing|focusing|specializing|with)\s+subjects\s+.*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'[,;\s]*core\s+subjects\s+.*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'[,;\s]*such\s+as\s+.*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'[,;\s]*completed\s+.*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'[,;\s]*(?:percentage|cgpa|score)[\s:-]*[0-9]+(?:\.[0-9]+)?%?.*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'[,;\s]*\b(19|20)\d{2}\b.*$', '', cleaned)
    cleaned = re.sub(r'\s+\b(?:in|scoring|with|from|at)\s*$', '', cleaned, flags=re.IGNORECASE).strip()
    parts = [_clean_field(p) for p in re.split(r'[,|]', cleaned) if _clean_field(p)]
    clean_parts = [p for p in parts if p.lower() not in ['state', 'general', 'na', 'n/a', '-']]
    if clean_parts:
        return ", ".join(clean_parts)
    return cleaned


def _parse_single_line_qual(line: str):
    """
    Parses a self-contained single line or sentence describing a qualification:
    e.g. 'Completed Bachelor of Technology in Computer Science from National Institute of Technology Karnataka, Surathkal in 2023 with a CGPA of 8.4.'
    """
    text = line
    grade, text = _extract_grade_field(text)
    year, text = _extract_year_field(text)
    text = re.sub(r'^(?:Completed|Graduated|Pursuing|Enrolled\s+in|Holds\s+a)\s+', '', text, flags=re.IGNORECASE)
    
    degree = ""
    inst = ""
    
    for pat in DEGREE_PATTERNS:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            d_start, d_end = m.start(), m.end()
            rest = text[d_end:]
            spec_match = re.search(r'^(?:\s+in\s+([A-Za-z\s&]+?))(?:\s+(?:from|at|,|\.|$))', rest, re.IGNORECASE)
            if spec_match:
                spec = spec_match.group(1).strip()
                degree = f"{text[d_start:d_end]} in {spec}"
                text = text[:d_start] + " " + rest[spec_match.end(1):]
            else:
                degree = text[d_start:d_end]
                text = text[:d_start] + " " + rest
            break

    inst_match = re.search(r'(?:from|at)\s+([A-Za-z0-9\s,\.\'\-]+?(?:University|College|Institute|School|Academy|Polytechnic|Vidyalaya)[A-Za-z0-9\s,\.\'\-]*)', text, re.IGNORECASE)
    if inst_match:
        inst = inst_match.group(1).strip(' ,.')
    else:
        parts = [_clean_field(p) for p in re.split(r'[,|]', text) if _clean_field(p)]
        inst_parts = [p for p in parts if _is_inst_kw(p)]
        if inst_parts:
            inst = ", ".join(inst_parts)

    degree = _format_degree_name(degree)
    inst = _clean_inst_name(inst)

    if degree or inst:
        return [degree or "—", inst or "—", year or "—", grade or "—"]
    return None


def _get_parsed_education_rows(edu_lines):
    """
    Universal dynamic education extraction pipeline.
    Works for ALL resume formats:
    - Tabular (pipe / tab / dash / space delimited)
    - Multi-line blocks
    - Paragraphs
    - Bullet points
    Extracts strictly from current candidate's resume; never hard-codes or invents details.
    """
    if not edu_lines:
        return []

    # Step 1: Combine fragmented lines (e.g. lines starting with 'and' or continuation of clauses)
    combined = []
    for line in edu_lines:
        l_str = _clean_field(line)
        if not l_str or _is_edu_header_line(l_str):
            continue
        if combined:
            prev = combined[-1]
            if (l_str.lower().startswith(('and ', 'or ', '& ', 'with ')) or 
                prev.lower().endswith(('such as', 'such as:', 'and', 'with', 'in', 'from', 'of', 'for', 'at', ',')) or
                (prev.lower().endswith(('engineering', 'technology', 'institute of', 'college of', 'school of', 'university of', 'national', 'state', 'central', 'government', 'govt')) and
                 l_str.lower().startswith(('college', 'university', 'institute', 'school', 'polytechnic', 'academy'))) or
                (not l_str[0].isupper() and not _is_degree_kw(l_str) and not _is_inst_kw(l_str))):
                combined[-1] = prev + " " + l_str
                continue
        combined.append(l_str)

    if not combined:
        return []

    # Step 2: Process lines into structured qualification records
    records = []
    current = {'degree': '', 'inst': '', 'year': '', 'grade': ''}

    def flush_current():
        nonlocal current
        deg = _format_degree_name(current['degree'])
        inst = _clean_inst_name(current['inst'])
        yr = current['year']
        gr = current['grade']
        if deg or inst:
            records.append([deg or "—", inst or "—", yr or "—", gr or "—"])
        current = {'degree': '', 'inst': '', 'year': '', 'grade': ''}

    for line in combined:
        # Delimited table row
        if '|' in line or '\t' in line:
            flush_current()
            parts = [_clean_field(p) for p in re.split(r'[|\t]', line) if _clean_field(p)]
            if any('degree' in p.lower() or 'course' in p.lower() for p in parts) and any('institution' in p.lower() or 'university' in p.lower() for p in parts):
                continue
            deg, inst, yr, gr = "", "", "", ""
            for p in parts:
                y_val, _ = _extract_year_field(p)
                g_val, _ = _extract_grade_field(p)
                if y_val and not yr: yr = y_val; continue
                if g_val and not gr: gr = g_val; continue
                if _is_degree_kw(p) and not deg: deg = p; continue
                if _is_inst_kw(p) and not inst: inst = p; continue
                if not inst: inst = p
            if deg or inst or yr or gr:
                records.append([_format_degree_name(deg) or "—", _clean_inst_name(inst) or "—", yr or "—", gr or "—"])
            continue

        y_val, y_rem = _extract_year_field(line)
        g_val, g_rem = _extract_grade_field(line)

        # Check if line is purely candidate summary, skills, or project description
        if _is_summary_or_non_edu(line):
            if g_val and not current['grade']:
                current['grade'] = g_val
            if y_val and not current['year']:
                current['year'] = y_val
            continue

        # Check if line has both degree and institution
        if _is_degree_kw(line) and _is_inst_kw(line):
            single = _parse_single_line_qual(line)
            if single and (single[0] != "—" and single[1] != "—"):
                if current['degree'] or current['inst']:
                    flush_current()
                current['degree'] = single[0]
                current['inst'] = single[1]
                if single[2] != "—" and not current['year']: current['year'] = single[2]
                if single[3] != "—" and not current['grade']: current['grade'] = single[3]
                if y_val and not current['year']: current['year'] = y_val
                if g_val and not current['grade']: current['grade'] = g_val
                continue

        has_deg = _is_degree_kw(line)
        has_inst = _is_inst_kw(line)

        if has_deg:
            if current['degree']:
                flush_current()
            
            deg_clean = line
            if g_val: deg_clean = deg_clean.replace(g_val, ' ')
            if y_val: deg_clean = deg_clean.replace(y_val, ' ')
            deg_clean = re.sub(r'^(?:percentage|cgpa|score)[\s:-]*[0-9]+(?:\.[0-9]+)?%?[\s,;:-]*', '', deg_clean, flags=re.IGNORECASE)
            deg_clean = re.sub(r'[,;\s]*(?:percentage|cgpa|score)[\s:-]*[0-9]+(?:\.[0-9]+)?%?.*$', '', deg_clean, flags=re.IGNORECASE)
            deg_clean = _clean_field(deg_clean)

            parts = [_clean_field(p) for p in re.split(r'[,|–—]', deg_clean) if _clean_field(p)]
            if len(parts) > 1 and _is_degree_kw(parts[0]):
                current['degree'] = parts[0]
                if not current['inst']:
                    current['inst'] = ", ".join(parts[1:])
            else:
                current['degree'] = deg_clean or line

            if y_val and not current['year']: current['year'] = y_val
            if g_val and not current['grade']: current['grade'] = g_val
            continue

        if has_inst:
            if current['inst']:
                if current['degree'] or current['year'] or current['grade']:
                    flush_current()
                    current['inst'] = line
                else:
                    if line.lower() not in current['inst'].lower():
                        current['inst'] += " " + line
            else:
                current['inst'] = line

            if y_val and not current['year']: current['year'] = y_val
            if g_val and not current['grade']: current['grade'] = g_val
            continue

        # Residual text
        if y_val:
            if current['year'] and (current['degree'] or current['inst']):
                flush_current()
            if not current['year']:
                current['year'] = y_val
        if g_val and not current['grade']:
            current['grade'] = g_val

        rem_str = _clean_field(y_rem.replace(g_val, '')) if y_val else _clean_field(g_rem)
        if rem_str and len(rem_str) < 90 and not _is_summary_or_non_edu(rem_str):
            if current['inst'] and rem_str.lower() not in current['inst'].lower():
                current['inst'] += ", " + rem_str
            elif not current['inst']:
                current['inst'] = rem_str

    flush_current()

    # Step 3: Deduplicate & merge records of same qualification
    merged = []
    for rec in records:
        deg, inst, yr, gr = rec
        match_idx = -1
        for idx, m in enumerate(merged):
            if deg != "—" and m[0] == deg:
                match_idx = idx
                break
            if "sslc" in deg.lower() and "sslc" in m[0].lower():
                match_idx = idx
                break
            if "puc" in deg.lower() and "puc" in m[0].lower():
                match_idx = idx
                break

        if match_idx >= 0:
            m = merged[match_idx]
            m_deg = m[0] if m[0] != "—" else deg
            m_inst = m[1] if (m[1] != "—" and len(m[1]) >= len(inst)) else (inst if inst != "—" else m[1])
            m_yr = m[2] if m[2] != "—" else yr
            m_gr = m[3] if m[3] != "—" else gr
            merged[match_idx] = [m_deg, m_inst, m_yr, m_gr]
        else:
            merged.append(rec)

    final_records = []
    for r in merged:
        if r[0] == "—" and r[1] == "—":
            continue
        final_records.append(r)

    return final_records


def _group_project_lines(proj_lines):
    entries = []
    temp_title = ""
    temp_link = ""
    temp_desc = []
    
    for line in proj_lines:
        line = line.strip()
        line = line.lstrip(" \t\n\r-*•·▪►").strip()
        if not line: continue
        
        words = line.split()
        capitalized_words = sum(1 for w in words if w and w[0].isupper())
        is_title_candidate = len(line) < 80 and not line.endswith(('.', ',', ';')) and (capitalized_words / len(words) > 0.4 if words else False)
        
        is_link_candidate = len(line) < 40 and ("github" in line.lower() or "http" in line.lower() or "link" in line.lower())
        
        if is_link_candidate:
            if temp_link:
                temp_link += " | " + line
            else:
                temp_link = line
        elif is_title_candidate and not temp_link and not temp_desc:
            if not temp_title:
                temp_title = line
            else:
                temp_desc.append(line)
        elif is_title_candidate and temp_desc:
            entries.append({"title": temp_title, "link": temp_link, "desc": " ".join(temp_desc)})
            temp_title = line
            temp_link = ""
            temp_desc = []
        else:
            if not temp_title:
                temp_title = line
            else:
                temp_desc.append(line)
                
    if temp_title or temp_desc:
        entries.append({"title": temp_title, "link": temp_link, "desc": " ".join(temp_desc)})
        
    return entries

def _extract_contacts(text: str):
    import re
    email = ""
    phone = ""
    linkedin = ""
    github = ""
    leetcode = ""
    
    email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
    if email_match: email = email_match.group(0)
        
    # Match phone numbers like 123-456-7890, (123) 456-7890, 1234567890, +91 1234567890
    phone_match = re.search(r'(\+\d{1,3}\s?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text)
    if phone_match: phone = phone_match.group(0)
        
    linkedin_match = re.search(r'linkedin\.com/in/[\w-]+', text, re.IGNORECASE)
    if linkedin_match: linkedin = linkedin_match.group(0)
        
    github_match = re.search(r'github\.com/[\w-]+', text, re.IGNORECASE)
    if github_match: github = github_match.group(0)

    leetcode_match = re.search(r'leetcode\.com/(?:u/)?[\w-]+', text, re.IGNORECASE)
    if leetcode_match: leetcode = leetcode_match.group(0)
        
    return email, phone, linkedin, github, leetcode

def _extract_name(resume_text: str, header_lines: list = None) -> str:
    """Robustly extract candidate name from header lines or top text."""
    import re
    if header_lines is None:
        header_lines = []
        
    # 1. Search for explicit "NAME:" or "Name:" pattern in the top 25 lines
    for line in header_lines + [l.strip() for l in resume_text.split('\n')[:25]]:
        clean_line = re.sub(r'[*#_]', '', line)
        if re.search(r'\bNAME\b', clean_line, re.IGNORECASE):
            parts = [p.strip(' |:\t') for p in re.split(r'[:|]', clean_line) if p.strip(' |:\t')]
            for p in parts:
                if p.lower() not in ['name', 'candidate name', 'applicant name'] and len(p) >= 2 and re.match(r'^[A-Za-z][A-Za-z\s.\'\-]+$', p):
                    return p
                    
    # 2. Look for first line in header that isn't a title/keyword
    for line in header_lines:
        clean = re.sub(r'^[#*|\s\-–—]+', '', line).strip()
        clean = re.sub(r'[#*|\s\-–—]+$', '', clean).strip()
        if not clean:
            continue
        low = clean.lower()
        if any(kw in low for kw in ['resume', 'curriculum vitae', 'cv', 'page', 'email', 'phone', 'mobile', 'address', 'contact', 'profile', 'summary', 'objective']):
            continue
        if 2 <= len(clean) <= 40 and re.match(r'^[A-Za-z][A-Za-z\s.\'\-]+$', clean):
            return clean
            
    # 3. Fallback from top lines of text
    for line in [l.strip() for l in resume_text.split('\n')[:10]]:
        clean = re.sub(r'^[#*|\s\-–—]+', '', line).strip()
        clean = re.sub(r'[#*|\s\-–—]+$', '', clean).strip()
        if not clean:
            continue
        low = clean.lower()
        if any(kw in low for kw in ['resume', 'curriculum vitae', 'cv', 'page', 'email', 'phone', 'mobile', 'address', 'contact', 'profile', 'summary', 'objective']):
            continue
        if 2 <= len(clean) <= 40 and re.match(r'^[A-Za-z][A-Za-z\s.\'\-]+$', clean):
            return clean

    if header_lines:
        cand = re.sub(r'^[#*|\s\-–—]+', '', header_lines[0]).strip()
        if cand.lower() not in ['resume', 'curriculum vitae', 'cv']:
            return cand
    return "Candidate Name"


def _extract_location(resume_text: str, pref_loc: str = "") -> str:
    """Extract location (city, state/country) from resume header or user preference."""
    if pref_loc and pref_loc.strip():
        return pref_loc.strip()
    import re
    lines = [line.strip() for line in resume_text.split('\n') if line.strip()][:15]
    for line in lines[1:]:  # skip candidate name line
        cleaned = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '', line)
        cleaned = re.sub(r'(\+\d{1,3}\s?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', '', cleaned)
        cleaned = re.sub(r'https?://\S+', '', cleaned)
        cleaned = re.sub(r'(?:linkedin|github|leetcode)\.com\S*', '', cleaned, flags=re.IGNORECASE)
        parts = [p.strip(' ,;:-|\t*#') for p in re.split(r'[|•·▪►◇\t]', cleaned)]
        for p in parts:
            if 3 <= len(p) <= 40 and any(c.isalpha() for c in p):
                low = p.lower()
                if not any(kw in low for kw in ['resume', 'curriculum', 'page', 'objective', 'summary', 'profile', 'education', 'skills', 'experience', 'projects', 'name', 'email', 'mobile', 'phone', 'dob', 'gender', 'language', 'hobby']):
                    return p
    return ""

def _parse_resume_sections(resume_text: str) -> dict:
    """Heuristic parser to chunk a resume into logical sections."""
    import re
    sections = {
        "Header": [], "Objective": [], "Education": [], "Skills": [],
        "Experience": [], "Projects": [], "Certifications": [], "Languages": [], "Other": []
    }
    
    current_section = "Header"
    lines = [line.strip() for line in resume_text.split('\n') if line.strip()]
    
    header_keywords = {
        "OBJECTIVE": "Objective", "SUMMARY": "Objective", "PROFILE": "Objective",
        "EDUCATION": "Education", "ACADEMIC": "Education",
        "SKILL": "Skills", "TECHNOLOGIES": "Skills", "TOOLS": "Skills",
        "EXPERIENCE": "Experience", "WORK": "Experience", "EMPLOYMENT": "Experience", "HISTORY": "Experience",
        "PROJECT": "Projects",
        "CERTIFICATION": "Certifications", "CERTIFICATE": "Certifications",
        "ACHIEVEMENT": "Certifications", "ACHIEVEMENTS": "Certifications",
        "LEADERSHIP": "Certifications", "AWARD": "Certifications", "AWARDS": "Certifications",
        "LANGUAGE": "Languages",
        "ADDITIONAL": "Other"
    }
    
    for line in lines:
        upper_line = line.upper()
        matched_section = None
        
        if len(line) < 30 and (line.isupper() or line.istitle() or line.endswith(':')):
            # Do not treat sub-qualifications as main section headers
            if not re.search(r'\b(?:secondary|higher\s+secondary|senior\s+secondary|primary)\s+education\b', upper_line, flags=re.IGNORECASE):
                for kw, sec in header_keywords.items():
                    if kw in upper_line:
                        matched_section = sec
                        break
        
        if matched_section:
            current_section = matched_section
        else:
            sections[current_section].append(line)
            
    # Post-processing: separate Certifications from Experience/Projects if mixed
    cert_keywords = ["certification", "certificate", "training", "bootcamp", "course", "simulation", "forage"]
    for sec_name in ["Experience", "Projects"]:
        if not sections[sec_name]: continue
        
        new_sec = []
        new_certs = []
        
        entries = _group_project_lines(sections[sec_name])
        for entry in entries:
            title_lower = entry["title"].lower()
            if any(kw in title_lower for kw in cert_keywords) and "developer" not in title_lower and "engineer" not in title_lower and "system" not in title_lower:
                new_certs.append(entry["title"])
                if entry["link"]: new_certs.append(entry["link"])
                if entry["desc"]: new_certs.append(entry["desc"])
            else:
                new_sec.append(entry["title"])
                if entry["link"]: new_sec.append(entry["link"])
                if entry["desc"]: new_sec.append(entry["desc"])
                
        sections[sec_name] = new_sec
        sections["Certifications"].extend(new_certs)

    import re
    extracted_langs = []
    for sec_name, lines_list in sections.items():
        if sec_name == "Languages": continue
        lines_to_keep = []
        for line in lines_list:
            clean_line = line.lstrip(" \t\n\r-*•·▪►").strip()
            lower_line = clean_line.lower()
            if "languages:" in lower_line:
                parts = re.split(r'(?i)languages:\s*', clean_line)
                if len(parts) > 1:
                    lang_part = parts[1]
                    for stop_word in ["Strengths:", "Skills:", "Hobbies:"]:
                        if stop_word.lower() in lang_part.lower():
                            lang_part = re.split(r'(?i)' + stop_word, lang_part)[0]
                    extracted_langs.append(lang_part.strip())
                    if parts[0].strip():
                        lines_to_keep.append(parts[0].strip())
            else:
                lines_to_keep.append(line)
        sections[sec_name] = lines_to_keep
        
    if extracted_langs:
        sections["Languages"].extend(extracted_langs)

    # Clean up languages by removing technical skills
    clean_langs = []
    for lang_line in sections["Languages"]:
        parts = [p.strip() for p in lang_line.split(',')]
        valid_parts = []
        for p in parts:
            if not p: continue
            if not extract_skills(p):
                valid_parts.append(p)
        if valid_parts:
            clean_langs.append(", ".join(valid_parts))
    sections["Languages"] = clean_langs

    return sections

def classify_skill_category(skill_name: str, given_cat: str = "") -> str:
    """
    Intelligently and dynamically classifies any skill based on its semantic nature and purpose.
    Never forces skills into rigid, inaccurate categories.
    """
    s_lower = (skill_name or "").strip().lower()
    if not s_lower:
        return "Other Technical Skills"

    canonical = ALIASES.get(s_lower, s_lower)
    resolved_cat = (given_cat or "").strip()
    if not resolved_cat or resolved_cat.lower() in ["general", "other", "unknown", "skill"]:
        resolved_cat = TECH_SKILLS.get(canonical, TECH_SKILLS.get(s_lower, ""))

    # 1. Soft Skills (strictly isolated from technical skills)
    soft_set = {
        "communication", "communication skills", "leadership", "teamwork", "team work",
        "collaboration", "team work and collaboration", "problem solving", "time management",
        "critical thinking", "adaptability", "work ethic", "creativity", "analytical thinking",
        "interpersonal skills", "conflict resolution", "public speaking", "mentoring",
        "decision making", "negotiation", "active listening", "emotional intelligence"
    }
    if s_lower in soft_set or canonical in soft_set or resolved_cat == "Soft Skills":
        return "Soft Skills"
    if any(k in s_lower for k in ["communication", "leadership", "teamwork", "collaboration", "interpersonal", "time management", "problem solving"]):
        return "Soft Skills"

    # 2. Programming Concepts (OOP, DSA, Design Patterns, System Design...)
    concept_set = {
        "oop", "object-oriented programming", "object oriented programming", "data structures",
        "algorithms", "data structures & algorithms", "data structures and algorithms", "dsa",
        "dbms", "operating systems", "os", "computer networks", "networking", "design patterns",
        "system design", "functional programming", "solid principles", "clean architecture",
        "mvc", "mvvm", "distributed systems", "multithreading", "concurrency", "threading"
    }
    if s_lower in concept_set or canonical in concept_set or resolved_cat == "Programming Concepts":
        return "Programming Concepts"
    if any(k in s_lower for k in ["object-oriented", "object oriented", "data structure", "algorithm", "design pattern", "solid principle", "clean architecture", "system design", "distributed system"]):
        return "Programming Concepts"

    # 3. API Technologies (REST, GraphQL, gRPC, SOAP...)
    api_set = {
        "rest", "rest api", "rest apis", "restful api", "restful apis", "graphql", "soap",
        "grpc", "webhooks", "webhook", "api design", "openapi", "swagger"
    }
    if s_lower in api_set or canonical in api_set or resolved_cat == "API Technologies":
        return "API Technologies"
    if (s_lower == "api" or "rest api" in s_lower or "restful" in s_lower or s_lower.endswith(" api") or s_lower.endswith(" apis")) and "fastapi" not in s_lower:
        return "API Technologies"

    # 4. Data Science (distinct from AI / Machine Learning)
    ds_set = {
        "data science", "data analysis", "data analytics", "pandas", "numpy", "matplotlib",
        "seaborn", "scipy", "plotly", "statistical analysis", "statistics", "tableau",
        "power bi", "powerbi", "business intelligence", "data visualization", "data mining",
        "eda", "exploratory data analysis"
    }
    if s_lower in ds_set or canonical in ds_set or resolved_cat in ["Data Science", "Data Analytics"]:
        return "Data Science"
    if any(k in s_lower for k in ["data science", "data analysis", "data analytic", "statistical", "statistics"]):
        return "Data Science"

    # 5. AI / Machine Learning
    aiml_set = {
        "machine learning", "ml", "deep learning", "dl", "artificial intelligence", "ai",
        "nlp", "natural language processing", "computer vision", "cv", "tensorflow", "tf",
        "pytorch", "keras", "scikit-learn", "sklearn", "opencv", "langchain", "llm", "llms",
        "large language model", "large language models", "transformers", "hugging face",
        "openai", "neural network", "neural networks", "generative ai", "genai",
        "prompt engineering", "reinforcement learning", "xgboost", "bert", "yolo", "rag"
    }
    if s_lower in aiml_set or canonical in aiml_set or resolved_cat in ["AI/ML", "AI / Machine Learning"]:
        return "AI / Machine Learning"
    if any(k in s_lower for k in ["machine learning", "deep learning", "artificial intelligence", "neural", "computer vision", "langchain", "generative ai"]):
        return "AI / Machine Learning"

    # 6. Databases
    db_set = {
        "postgresql", "postgres", "mongodb", "mongo", "mysql", "sql", "nosql", "oracle",
        "sqlite", "sql server", "redis", "cassandra", "firebase", "firestore", "dynamodb",
        "mariadb", "neo4j", "snowflake", "bigquery", "supabase", "couchdb", "mongoose",
        "hive", "hbase", "db2", "elasticsearch"
    }
    if s_lower in db_set or canonical in db_set or resolved_cat in ["Database", "Databases"]:
        return "Databases"
    if s_lower.endswith("db") or "database" in s_lower or s_lower.startswith("sql"):
        return "Databases"

    # 7. Backend Technologies
    backend_set = {
        "node.js", "nodejs", "node", "express", "express.js", "expressjs", "django",
        "flask", "fastapi", "spring", "spring boot", "rails", "ruby on rails", "laravel",
        "asp.net", "dotnet", ".net", ".net core", "microservices", "celery", "kafka",
        "rabbitmq"
    }
    if s_lower in backend_set or canonical in backend_set or resolved_cat in ["Backend", "Backend Technologies"]:
        return "Backend Technologies"

    # 8. Web Technologies (HTML, CSS, JSON, XML, WebSockets...)
    web_set = {
        "html", "html5", "css", "css3", "html/css", "xml", "json", "websockets",
        "websocket", "ajax", "jquery", "responsive design", "web design", "dom",
        "sass", "scss", "less"
    }
    if s_lower in web_set or canonical in web_set:
        return "Web Technologies"
    if resolved_cat in ["Web", "Web Technologies", "Web Technology"]:
        return "Web Technologies"

    # 9. Frontend Frameworks / Libraries
    frontend_set = {
        "react", "react.js", "reactjs", "angular", "angularjs", "vue", "vue.js", "vuejs",
        "next.js", "nextjs", "nuxt", "nuxt.js", "vite", "bootstrap", "tailwind",
        "tailwind css", "tailwindcss", "svelte", "ember", "gatsby", "redux", "mobx",
        "material-ui", "material ui", "chakra ui", "shadcn", "zustand", "webpack", "parcel"
    }
    if s_lower in frontend_set or canonical in frontend_set or resolved_cat in ["Frontend", "Frontend Frameworks / Libraries"]:
        return "Frontend Frameworks / Libraries"

    # 10. Programming Languages
    lang_set = {
        "python", "java", "c", "c++", "c#", "javascript", "typescript", "r", "go",
        "golang", "ruby", "kotlin", "swift", "php", "rust", "scala", "dart", "perl",
        "matlab", "bash", "shell scripting", "shell", "powershell", "lua", "julia",
        "groovy", "solidity", "haskell", "elixir", "clojure", "objective-c", "assembly",
        "cobol", "fortran"
    }
    if s_lower in lang_set or canonical in lang_set or resolved_cat in ["Programming", "Programming Languages"]:
        return "Programming Languages"
    if s_lower == "javascript" or s_lower.endswith("script"):
        return "Programming Languages"

    # 11. Version Control (distinct from DevOps / Cloud)
    vc_set = {
        "git", "github", "gitlab", "bitbucket", "svn", "version control"
    }
    if s_lower in vc_set or canonical in vc_set or resolved_cat == "Version Control":
        return "Version Control"

    # 12. Tools / Platforms (VS Code, Postman, Jupyter Notebook, Eclipse, IntelliJ IDEA...)
    tools_set = {
        "vs code", "vscode", "visual studio code", "visual studio", "pycharm", "intellij",
        "intellij idea", "eclipse", "latex", "google collab", "google colab", "postman",
        "jupyter", "jupyter notebook", "jira", "confluence", "notion", "figma", "photoshop"
    }
    if s_lower in tools_set or canonical in tools_set or resolved_cat in ["Tools", "Platforms", "Tools / Platforms"]:
        return "Tools / Platforms"

    # 13. DevOps / Cloud
    devops_set = {
        "docker", "kubernetes", "k8s", "aws", "aws cloud", "amazon web services", "azure",
        "microsoft azure", "azure cloud", "gcp", "google cloud", "google cloud platform",
        "serverless", "cloudformation", "jenkins", "github actions", "gitlab ci", "ci/cd",
        "ci / cd", "devops", "terraform", "ansible", "chef", "puppet", "helm", "prometheus",
        "grafana", "datadog", "linux", "unix"
    }
    if s_lower in devops_set or canonical in devops_set or resolved_cat in ["Cloud", "DevOps", "DevOps / Cloud"]:
        return "DevOps / Cloud"

    # 14. Testing
    test_set = {
        "selenium", "cypress", "jest", "pytest", "junit", "testng", "playwright",
        "unit testing", "integration testing", "automated testing", "tdd", "bdd",
        "mocha", "chai", "karma", "testing"
    }
    if s_lower in test_set or canonical in test_set or resolved_cat == "Testing":
        return "Testing"

    # 15. Cybersecurity
    sec_set = {
        "cybersecurity", "ethical hacking", "penetration testing", "pen testing", "owasp",
        "network security", "information security", "cryptography", "ssl", "tls",
        "oauth", "jwt", "encryption", "security"
    }
    if s_lower in sec_set or canonical in sec_set or resolved_cat in ["Security", "Cybersecurity"]:
        return "Cybersecurity"

    # 16. Finance & Accounting
    fin_set = {
        "accounting", "accountancy", "financial accounting", "cost accounting", "management accounting",
        "corporate finance", "auditing", "audit", "internal audit", "financial audit", "taxation",
        "tax planning", "income tax", "gst", "vat", "tally", "tally prime", "tally erp", "quickbooks",
        "sap fico", "financial modeling", "financial reporting", "financial analysis", "accounts payable",
        "accounts receivable", "payroll", "bank reconciliation", "reconciliation", "balance sheet",
        "cash flow", "budgeting", "financial forecasting", "cpa", "acca", "chartered accountancy",
        "credit analysis", "banking", "finance", "compliance"
    }
    if s_lower in fin_set or canonical in fin_set or resolved_cat in ["Finance", "Finance & Accounting", "Accounting"]:
        return "Finance & Accounting"

    # 17. Business & Management
    mgmt_set = {
        "business analysis", "requirements gathering", "stakeholder management", "gap analysis",
        "process improvement", "swot analysis", "feasibility study", "kpis", "kpi", "business process",
        "risk management", "business intelligence", "agile", "scrum", "jira", "kanban", "sprint planning"
    }
    if s_lower in mgmt_set or canonical in mgmt_set or resolved_cat in ["Business & Management", "Management"]:
        return "Business & Management"

    # 18. HR & People Operations
    hr_set = {
        "recruitment", "talent acquisition", "human resources", "hr", "sourcing", "screening",
        "interviewing", "employee onboarding", "onboarding", "employee engagement", "hr policies",
        "payroll administration", "performance management", "employee relations", "ats", "ats screening"
    }
    if s_lower in hr_set or canonical in hr_set or resolved_cat in ["HR & Operations", "HR", "Human Resources"]:
        return "HR & Operations"

    # 19. Marketing & Growth
    mktg_set = {
        "digital marketing", "seo", "sem", "social media marketing", "content marketing",
        "content writing", "copywriting", "email marketing", "google analytics", "campaign management",
        "lead generation", "crm", "hubspot", "branding", "growth marketing"
    }
    if s_lower in mktg_set or canonical in mktg_set or resolved_cat in ["Marketing & Growth", "Marketing"]:
        return "Marketing & Growth"

    # 20. Core Engineering (Embedded / Hardware / Mechanical / Civil)
    core_eng_set = {
        "embedded systems", "embedded", "microcontrollers", "arduino", "raspberry pi", "iot",
        "circuit design", "pcb design", "vlsi", "verilog", "vhdl", "plc", "scada", "power systems",
        "renewable energy", "sensors", "cad", "autocad", "solidworks", "ansys", "electronics"
    }
    if s_lower in core_eng_set or canonical in core_eng_set or resolved_cat in ["Core Engineering", "Engineering"]:
        return "Core Engineering"

    # Semantic keyword inferences
    if any(k in s_lower for k in ["cloud", "docker", "deploy", "server", "ci", "cd"]):
        return "DevOps / Cloud"
    if any(k in s_lower for k in ["test", "qa"]):
        return "Testing"
    if any(k in s_lower for k in ["tool", "ide"]):
        return "Tools / Platforms"
    if any(k in s_lower for k in ["security", "crypto", "hack"]):
        return "Cybersecurity"
    if any(k in s_lower for k in ["tax", "audit", "account", "ledger", "balance sheet", "tally"]):
        return "Finance & Accounting"
    if any(k in s_lower for k in ["recruit", "onboard", "talent", "human resource"]):
        return "HR & Operations"
    if any(k in s_lower for k in ["marketing", "seo", "campaign"]):
        return "Marketing & Growth"
    if any(k in s_lower for k in ["embedded", "microcontroller", "circuit", "pcb", "iot", "autocad"]):
        return "Core Engineering"
    if any(k in s_lower for k in ["api", "soap"]):
        return "API Technologies"
    if any(k in s_lower for k in ["data science", "analytic", "statistic"]):
        return "Data Science"
    if any(k in s_lower for k in ["ai", "ml", "model", "neural"]):
        return "AI / Machine Learning"
    if any(k in s_lower for k in ["framework", "react", "vue", "angular", "ui"]):
        return "Frontend Frameworks / Libraries"
    if any(k in s_lower for k in ["boot", "frame", "engine", "back"]):
        return "Backend Technologies"
    if any(k in s_lower for k in ["concept", "algorithm", "structure"]):
        return "Programming Concepts"

    return "Other Technical Skills"


def _categorize_skills(resume_skills_data, missing_skills_data=None):
    """
    Intelligently and dynamically categorizes skills into technical categories and soft skills.
    Returns: (tech_categories_dict, soft_skills_list)
    - tech_categories_dict: {category_name: [{"name": display_name, "is_missing": bool}, ...]}
      Only categories with at least 1 skill are included (no empty categories).
    - soft_skills_list: [{"name": display_name, "is_missing": bool}, ...]
    """
    category_order = [
        "Programming Languages",
        "Programming Concepts",
        "Web Technologies",
        "Frontend Frameworks / Libraries",
        "Backend Technologies",
        "API Technologies",
        "Databases",
        "AI / Machine Learning",
        "Data Science",
        "DevOps / Cloud",
        "Core Engineering",
        "Finance & Accounting",
        "Business & Management",
        "HR & Operations",
        "Marketing & Growth",
        "Version Control",
        "Testing",
        "Cybersecurity",
        "Tools / Platforms",
        "Other Technical Skills"
    ]

    proper_casing = {
        # Non-Tech: Finance & Accounting
        "tally": "Tally Prime",
        "tally prime": "Tally Prime",
        "tally erp": "Tally ERP",
        "quickbooks": "QuickBooks",
        "sap fico": "SAP FICO",
        "gst": "GST",
        "vat": "VAT",
        "cpa": "CPA",
        "acca": "ACCA",
        "financial modeling": "Financial Modeling",
        "financial accounting": "Financial Accounting",
        "auditing": "Auditing",
        "balance sheet": "Balance Sheet",
        "cash flow": "Cash Flow Analysis",

        # Non-Tech: Business & Management
        "business analysis": "Business Analysis",
        "requirements gathering": "Requirements Gathering",
        "stakeholder management": "Stakeholder Management",
        "project management": "Project Management",
        "jira": "JIRA",
        "swot analysis": "SWOT Analysis",
        "gap analysis": "Gap Analysis",

        # Non-Tech: HR & Operations
        "recruitment": "Recruitment",
        "talent acquisition": "Talent Acquisition",
        "human resources": "Human Resources",
        "employee onboarding": "Employee Onboarding",
        "employee engagement": "Employee Engagement",
        "payroll administration": "Payroll Administration",

        # Non-Tech: Marketing & Growth
        "digital marketing": "Digital Marketing",
        "seo": "SEO",
        "sem": "SEM",
        "google analytics": "Google Analytics",
        "social media marketing": "Social Media Marketing",
        "content marketing": "Content Marketing",
        "crm": "CRM",
        "hubspot": "HubSpot",

        # Core Engineering & Hardware
        "embedded systems": "Embedded Systems",
        "iot": "IoT",
        "microcontrollers": "Microcontrollers",
        "pcb design": "PCB Design",
        "vlsi": "VLSI",
        "verilog": "Verilog",
        "vhdl": "VHDL",
        "plc": "PLC",
        "scada": "SCADA",
        "autocad": "AutoCAD",
        "solidworks": "SolidWorks",
        "ansys": "ANSYS",

        # Soft Skills
        "communication": "Communication",
        "communication skills": "Communication",
        "leadership": "Leadership",
        "teamwork": "Teamwork",
        "team work": "Teamwork",
        "team work and collaboration": "Teamwork & Collaboration",
        "collaboration": "Teamwork & Collaboration",
        "problem solving": "Problem Solving",
        "time management": "Time Management",
        "critical thinking": "Critical Thinking",
        "adaptability": "Adaptability",

        # Programming Concepts
        "oop": "OOP",
        "object-oriented programming": "OOP",
        "object oriented programming": "OOP",
        "data structures": "Data Structures",
        "algorithms": "Algorithms",
        "data structures and algorithms": "Data Structures & Algorithms",
        "dsa": "Data Structures & Algorithms",
        "dbms": "DBMS",
        "operating systems": "Operating Systems",
        "computer networks": "Computer Networks",
        "design patterns": "Design Patterns",
        "system design": "System Design",
        "distributed systems": "Distributed Systems",
        "solid principles": "SOLID Principles",
        "clean architecture": "Clean Architecture",

        # API Technologies
        "rest": "REST APIs",
        "rest api": "REST APIs",
        "rest apis": "REST APIs",
        "restful api": "REST APIs",
        "restful apis": "REST APIs",
        "graphql": "GraphQL",
        "soap": "SOAP",
        "grpc": "gRPC",

        # Data Science
        "data science": "Data Science",
        "data analysis": "Data Analysis",
        "data analytics": "Data Analytics",
        "pandas": "Pandas",
        "numpy": "NumPy",
        "matplotlib": "Matplotlib",
        "seaborn": "Seaborn",
        "scipy": "SciPy",
        "statistical analysis": "Statistical Analysis",

        # AI / Machine Learning
        "machine learning": "Machine Learning",
        "deep learning": "Deep Learning",
        "artificial intelligence": "Artificial Intelligence",
        "ai": "Artificial Intelligence",
        "nlp": "NLP",
        "natural language processing": "NLP",
        "computer vision": "Computer Vision",
        "tensorflow": "TensorFlow",
        "pytorch": "PyTorch",
        "keras": "Keras",
        "scikit-learn": "scikit-learn",
        "sklearn": "scikit-learn",
        "opencv": "OpenCV",
        "langchain": "LangChain",
        "llm": "LLMs",
        "llms": "LLMs",
        "openai": "OpenAI",

        # Databases
        "postgresql": "PostgreSQL",
        "postgres": "PostgreSQL",
        "mongodb": "MongoDB",
        "mongo": "MongoDB",
        "mysql": "MySQL",
        "sql": "SQL",
        "nosql": "NoSQL",
        "oracle": "Oracle",
        "sqlite": "SQLite",
        "sql server": "SQL Server",
        "redis": "Redis",
        "cassandra": "Cassandra",
        "firebase": "Firebase",
        "firestore": "Firestore",
        "dynamodb": "DynamoDB",
        "mariadb": "MariaDB",
        "snowflake": "Snowflake",
        "bigquery": "BigQuery",
        "supabase": "Supabase",

        # Backend Technologies
        "node.js": "Node.js",
        "nodejs": "Node.js",
        "node": "Node.js",
        "express": "Express.js",
        "express.js": "Express.js",
        "expressjs": "Express.js",
        "django": "Django",
        "flask": "Flask",
        "fastapi": "FastAPI",
        "spring": "Spring Boot",
        "spring boot": "Spring Boot",
        "rails": "Ruby on Rails",
        "ruby on rails": "Ruby on Rails",
        "laravel": "Laravel",
        "asp.net": "ASP.NET",
        "dotnet": ".NET",
        "microservices": "Microservices",
        "kafka": "Kafka",
        "rabbitmq": "RabbitMQ",

        # Frontend Frameworks / Libraries
        "react": "React.js",
        "react.js": "React.js",
        "reactjs": "React.js",
        "angular": "Angular",
        "angularjs": "Angular",
        "vue": "Vue.js",
        "vue.js": "Vue.js",
        "vuejs": "Vue.js",
        "next.js": "Next.js",
        "nextjs": "Next.js",
        "nuxt": "Nuxt.js",
        "svelte": "Svelte",
        "tailwind": "Tailwind CSS",
        "tailwind css": "Tailwind CSS",
        "tailwindcss": "Tailwind CSS",
        "bootstrap": "Bootstrap",
        "redux": "Redux",
        "vite": "Vite",

        # Web Technologies
        "html": "HTML",
        "html5": "HTML5",
        "css": "CSS",
        "css3": "CSS3",
        "html/css": "HTML/CSS",
        "json": "JSON",
        "xml": "XML",
        "ajax": "AJAX",
        "jquery": "jQuery",
        "websockets": "WebSockets",
        "websocket": "WebSockets",

        # Programming Languages
        "python": "Python",
        "java": "Java",
        "c": "C",
        "c++": "C++",
        "c#": "C#",
        "javascript": "JavaScript",
        "typescript": "TypeScript",
        "r": "R",
        "go": "Go",
        "golang": "Go",
        "kotlin": "Kotlin",
        "swift": "Swift",
        "ruby": "Ruby",
        "php": "PHP",
        "rust": "Rust",
        "scala": "Scala",
        "dart": "Dart",
        "perl": "Perl",
        "matlab": "MATLAB",
        "bash": "Bash",
        "shell scripting": "Shell Scripting",
        "powershell": "PowerShell",

        # DevOps / Cloud
        "docker": "Docker",
        "kubernetes": "Kubernetes",
        "k8s": "Kubernetes",
        "aws": "AWS",
        "aws cloud": "AWS",
        "amazon web services": "AWS",
        "azure": "Azure",
        "microsoft azure": "Azure",
        "azure cloud": "Azure",
        "gcp": "Google Cloud",
        "google cloud": "Google Cloud",
        "ci/cd": "CI/CD",
        "github actions": "GitHub Actions",
        "gitlab ci": "GitLab CI",
        "jenkins": "Jenkins",
        "terraform": "Terraform",
        "ansible": "Ansible",
        "devops": "DevOps",
        "linux": "Linux",
        "unix": "Unix",

        # Version Control
        "git": "Git",
        "github": "GitHub",
        "gitlab": "GitLab",
        "bitbucket": "Bitbucket",

        # Tools / Platforms
        "vs code": "VS Code",
        "vscode": "VS Code",
        "pycharm": "PyCharm",
        "intellij": "IntelliJ IDEA",
        "intellij idea": "IntelliJ IDEA",
        "eclipse": "Eclipse",
        "postman": "Postman",
        "jupyter": "Jupyter Notebook",
        "jupyter notebook": "Jupyter Notebook",
        "jira": "Jira",
        "confluence": "Confluence",
        "notion": "Notion",
        "figma": "Figma",
        "latex": "LaTeX",

        # Testing
        "selenium": "Selenium",
        "cypress": "Cypress",
        "jest": "Jest",
        "pytest": "PyTest",
        "junit": "JUnit",
        "playwright": "Playwright",

        # Cybersecurity
        "cybersecurity": "Cybersecurity",
        "ethical hacking": "Ethical Hacking",
        "penetration testing": "Penetration Testing",
        "owasp": "OWASP",
    }

    # Set of skills originally present in the candidate's uploaded resume
    resume_skill_set = set()
    for s in (resume_skills_data or []):
        if isinstance(s, dict):
            s_name = (s.get("skill") or s.get("name") or "").strip().lower()
        else:
            s_name = str(s).strip().lower()
        if s_name:
            resume_skill_set.add(s_name)
            canon = ALIASES.get(s_name, s_name).lower()
            resume_skill_set.add(canon)
            for k, v in ALIASES.items():
                if v.lower() == s_name or v.lower() == canon:
                    resume_skill_set.add(k.lower())
            if s_name.endswith(".js"): resume_skill_set.add(s_name[:-3])
            if s_name.endswith(" api"): resume_skill_set.add(s_name[:-4])
            if s_name.endswith(" apis"): resume_skill_set.add(s_name[:-5])

    # Build initial list of items: resume skills first, followed by missing skills
    items_to_categorize = []
    for s_obj in (resume_skills_data or []):
        items_to_categorize.append((s_obj, False))
    for m_obj in (missing_skills_data or []):
        items_to_categorize.append((m_obj, True))

    seen_skills = set()
    temp_categories = {cat: [] for cat in category_order}
    soft_skills = []

    for item, from_missing_list in items_to_categorize:
        if isinstance(item, dict):
            s_name = (item.get("skill") or item.get("name") or "").strip()
            item_cat = item.get("category", "")
        else:
            s_name = str(item).strip()
            item_cat = ""

        if not s_name:
            continue

        s_lower = s_name.lower()
        canonical_key = ALIASES.get(s_lower, s_lower)
        display_name = proper_casing.get(canonical_key, proper_casing.get(s_lower, s_name if (any(c.isupper() for c in s_name) or '/' in s_name) else s_name.title()))
        disp_lower = display_name.lower()

        # A skill is considered present (black) ONLY if it was originally in candidate's uploaded resume.
        is_in_resume = bool(
            s_lower in resume_skill_set or
            canonical_key in resume_skill_set or
            disp_lower in resume_skill_set
        )

        # Do not add a missing skill if it already exists in the candidate's resume
        if from_missing_list and is_in_resume:
            continue

        is_missing = not is_in_resume

        # Duplicate check across categories/casing
        check_keys = {disp_lower, canonical_key, s_lower}
        if s_lower.endswith(".js"): check_keys.add(s_lower[:-3])
        if s_lower.endswith(" api"): check_keys.add(s_lower[:-4])
        if s_lower.endswith(" apis"): check_keys.add(s_lower[:-5])
        if disp_lower.endswith(".js"): check_keys.add(disp_lower[:-3])
        if disp_lower.endswith(" api"): check_keys.add(disp_lower[:-4])
        if disp_lower.endswith(" apis"): check_keys.add(disp_lower[:-5])

        if any(k in seen_skills for k in check_keys):
            continue

        for k in check_keys:
            seen_skills.add(k)

        category = classify_skill_category(s_name, item_cat)
        skill_entry = {"name": display_name, "is_missing": is_missing}

        if category == "Soft Skills":
            soft_skills.append(skill_entry)
        else:
            if category not in temp_categories:
                temp_categories[category] = []
            temp_categories[category].append(skill_entry)

    # Return only categories that contain skills (Rule: Do NOT create empty categories)
    tech_categories = {cat: skills for cat, skills in temp_categories.items() if skills}
    return tech_categories, soft_skills


def _format_summary(short_bio: str = "", extracted_obj: str = "") -> str:
    import re
    raw = (short_bio or extracted_obj or "").strip()
    if raw:
        # Split into sentences
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', raw) if s.strip()]
        chosen = []
        word_count = 0
        for s in sentences:
            s_words = s.split()
            if not chosen:
                chosen.append(s)
                word_count += len(s_words)
            elif word_count + len(s_words) <= 45:
                chosen.append(s)
                word_count += len(s_words)
            else:
                break
        res = " ".join(chosen).strip()
        if res and not res.endswith(('.', '!', '?')):
            res += "."
        return res
    return "Aspiring engineer skilled in problem-solving and modern technologies, eager to contribute effectively to dynamic engineering teams."


def generate_tailored_resume(resume_text: str, job_text: str, short_bio: str = "", pref_title: str = "", pref_loc: str = "", extra_missing_skills: list = None, template: str = "modern") -> str:
    """
    Generate a tailored resume offline matching the exact professional template format.
    Supports templates: 'modern', 'classic', 'compact'.
    """
    try:
        resume_skills_data = extract_skills(resume_text)
        job_skills_data = extract_skills(job_text)
        result = match_skills(resume_skills_data, job_skills_data, threshold=0.72)
        
        sections = _parse_resume_sections(resume_text)
        name = _extract_name(resume_text, sections.get("Header", []))
        
        loc = _extract_location(resume_text, pref_loc)
        email, phone, linkedin, github, leetcode = _extract_contacts(resume_text)
        
        email_str = f'<a href="mailto:{email}" target="_blank" rel="noopener noreferrer">{email}</a>' if email else ""
        phone_str = phone if phone else ""
        linkedin_str = f'<a href="https://{linkedin}" target="_blank" rel="noopener noreferrer">{linkedin}</a>' if linkedin else ""
        github_str = f'<a href="https://{github}" target="_blank" rel="noopener noreferrer">{github}</a>' if github else ""
        leetcode_str = f'<a href="https://{leetcode}" target="_blank" rel="noopener noreferrer">{leetcode}</a>' if leetcode else ""
        
        # Row 1: Primary Contact (Location, Phone, Email)
        row1_items = []
        if loc: row1_items.append(f'<span class="contact-item">{loc}</span>')
        if phone_str: row1_items.append(f'<span class="contact-item">{phone_str}</span>')
        if email_str: row1_items.append(f'<span class="contact-item">{email_str}</span>')
        
        # Row 2: Professional Profiles (LinkedIn, GitHub, LeetCode)
        row2_items = []
        if linkedin_str: row2_items.append(f'<span class="contact-item">{linkedin_str}</span>')
        if github_str: row2_items.append(f'<span class="contact-item">{github_str}</span>')
        if leetcode_str: row2_items.append(f'<span class="contact-item">{leetcode_str}</span>')
        
        sep_html = '<span class="contact-sep">|</span>'
        total_text_len = len(loc) + len(phone_str) + len(email) + len(linkedin) + len(github) + len(leetcode)
        if len(row1_items) + len(row2_items) <= 3 and total_text_len <= 70 and not github_str:
            all_items = row1_items + row2_items
            contact_line_html = f'<div class="contact-row">{f" {sep_html} ".join(all_items)}</div>' if all_items else f'<div class="contact-row"><span class="contact-item">email@example.com</span></div>'
        else:
            rows = []
            if row1_items:
                rows.append(f'<div class="contact-row">{f" {sep_html} ".join(row1_items)}</div>')
            if row2_items:
                rows.append(f'<div class="contact-row">{f" {sep_html} ".join(row2_items)}</div>')
            contact_line_html = "\n    ".join(rows) if rows else '<div class="contact-row"><span class="contact-item">email@example.com</span></div>'

        # Summary (concise max 1.5 - 2 lines)
        extracted_obj = " ".join(sections.get("Objective", [])).strip()
        bio = _format_summary(short_bio, extracted_obj)

        # Ensure all missing skills from job description, match results, and extra inputs are included
        resume_skill_set = set()
        for s in (resume_skills_data or []):
            if isinstance(s, dict):
                s_name = (s.get("skill") or s.get("name") or "").strip().lower()
            else:
                s_name = str(s).strip().lower()
            if s_name:
                resume_skill_set.add(s_name)
                canon = ALIASES.get(s_name, s_name).lower()
                resume_skill_set.add(canon)
                for k, v in ALIASES.items():
                    if v.lower() == s_name or v.lower() == canon:
                        resume_skill_set.add(k.lower())

        all_missing_skills = []
        for s in (job_skills_data or []):
            if isinstance(s, dict):
                val = (s.get("skill") or s.get("name") or "").strip().lower()
                if val and val not in resume_skill_set and ALIASES.get(val, "") not in resume_skill_set:
                    all_missing_skills.append(s)
            elif isinstance(s, str) and s.strip():
                val = s.strip().lower()
                if val and val not in resume_skill_set and ALIASES.get(val, "") not in resume_skill_set:
                    all_missing_skills.append({"skill": s.strip(), "category": TECH_SKILLS.get(val, "General")})

        extra_list = []
        if extra_missing_skills:
            for em in extra_missing_skills:
                if isinstance(em, dict):
                    s_name = (em.get("skill") or em.get("name") or "").strip()
                    if s_name:
                        cat = em.get("category") or TECH_SKILLS.get(s_name.lower(), "General")
                        extra_list.append({"skill": s_name, "category": cat})
                elif isinstance(em, str) and em.strip():
                    em_str = em.strip()
                    cat = TECH_SKILLS.get(em_str.lower(), "General")
                    extra_list.append({"skill": em_str, "category": cat})

        missing_pool = []
        seen_missing = set()
        for s in (result.get("missingSkills", []) + all_missing_skills + extra_list):
            if isinstance(s, dict):
                s_name = (s.get("skill") or s.get("name") or "").strip()
                s_low = s_name.lower()
                canon = ALIASES.get(s_low, s_low).lower()
                if s_low and s_low not in seen_missing and canon not in seen_missing:
                    seen_missing.add(s_low)
                    seen_missing.add(canon)
                    cat = s.get("category") or TECH_SKILLS.get(canon, TECH_SKILLS.get(s_low, "General"))
                    missing_pool.append({"skill": s_name, "category": cat})
            elif isinstance(s, str) and s.strip():
                s_str = s.strip()
                s_low = s_str.lower()
                canon = ALIASES.get(s_low, s_low).lower()
                if s_low and s_low not in seen_missing and canon not in seen_missing:
                    seen_missing.add(s_low)
                    seen_missing.add(canon)
                    cat = TECH_SKILLS.get(canon, TECH_SKILLS.get(s_low, "General"))
                    missing_pool.append({"skill": s_str, "category": cat})

        # Skills categorization
        tech_cats, soft_skills = _categorize_skills(resume_skills_data, missing_pool)

        markdown = f"""<div class="resume-header">
  <h1 class="resume-name">{name.upper()}</h1>
  <div class="header-contact">{contact_line_html}</div>
</div>

## PROFESSIONAL SUMMARY
{bio}

## EDUCATION
"""
        if sections["Education"]:
            parsed_edu = _get_parsed_education_rows(sections["Education"])
            edu_rows = []
            for deg_v, inst_v, yr_v, gr_v in parsed_edu:
                deg_cell = deg_v if deg_v else "-"
                inst_cell = inst_v if inst_v else "-"
                yr_cell = yr_v if yr_v else "-"
                gr_cell = gr_v if gr_v else "-"
                edu_rows.append(
                    f'    <tr>\n'
                    f'      <td style="padding: 5px 8px; border: 1px solid #cbd5e1; vertical-align: middle;"><strong>{deg_cell}</strong></td>\n'
                    f'      <td style="padding: 5px 8px; border: 1px solid #cbd5e1; vertical-align: middle;">{inst_cell}</td>\n'
                    f'      <td style="padding: 5px 8px; border: 1px solid #cbd5e1; text-align: center; white-space: nowrap; vertical-align: middle;">{yr_cell}</td>\n'
                    f'      <td style="padding: 5px 8px; border: 1px solid #cbd5e1; text-align: center; white-space: nowrap; vertical-align: middle;">{gr_cell}</td>\n'
                    f'    </tr>'
                )
            if edu_rows:
                markdown += (
                    '<table class="education-table" style="width: 100%; border-collapse: collapse; margin: 6px 0 14px 0; font-size: 9.5pt;">\n'
                    '  <thead>\n'
                    '    <tr style="background-color: #f1f5f9;">\n'
                    '      <th style="padding: 6px 8px; border: 1px solid #cbd5e1; text-align: left; font-weight: 700; width: 28%;">Course / Degree</th>\n'
                    '      <th style="padding: 6px 8px; border: 1px solid #cbd5e1; text-align: left; font-weight: 700; width: 42%;">Institution / University</th>\n'
                    '      <th style="padding: 6px 8px; border: 1px solid #cbd5e1; text-align: center; font-weight: 700; width: 14%;">Year of Passing</th>\n'
                    '      <th style="padding: 6px 8px; border: 1px solid #cbd5e1; text-align: center; font-weight: 700; width: 16%;">Percentage / CGPA</th>\n'
                    '    </tr>\n'
                    '  </thead>\n'
                    '  <tbody>\n'
                    + "\n".join(edu_rows) + "\n"
                    '  </tbody>\n'
                    '</table>\n\n'
                )
            else:
                markdown += "N/A\n\n"
        else:
            markdown += "N/A\n\n"

        markdown += "\n\n## TECHNICAL SKILLS\n\n<table class=\"skills-table\">\n"
        for cat, skills_list in tech_cats.items():
            if skills_list:
                formatted_skills = []
                for s in skills_list:
                    s_name = s["name"] if isinstance(s, dict) else str(s)
                    is_missing = s.get("is_missing", False) if isinstance(s, dict) else False
                    if is_missing:
                        formatted_skills.append(f'<span class="missing-skill" style="color: red; font-weight: 700;">{s_name}</span>')
                    else:
                        formatted_skills.append(f'<span class="existing-skill">{s_name}</span>')
                s_str = ", ".join(formatted_skills)
                markdown += f"  <tr><td style=\"width: 225px;\"><strong>{cat}:</strong></td><td>{s_str}</td></tr>\n"

        if soft_skills:
            formatted_soft = []
            for s in soft_skills:
                s_name = s["name"] if isinstance(s, dict) else str(s)
                is_missing = s.get("is_missing", False) if isinstance(s, dict) else False
                if is_missing:
                    formatted_soft.append(f'<span class="missing-skill" style="color: red; font-weight: 700;">{s_name}</span>')
                else:
                    formatted_soft.append(f'<span class="existing-skill">{s_name}</span>')
            soft_str = ", ".join(formatted_soft)
            markdown += f"  <tr><td style=\"width: 225px;\"><strong>Soft Skills:</strong></td><td>{soft_str}</td></tr>\n"

        markdown += "</table>\n\n"

        combined_projects = sections["Projects"]
        if combined_projects:
            markdown += "\n\n## PROJECTS\n\n"
            proj_entries = _group_project_lines(combined_projects)
            for entry in proj_entries:
                title = entry["title"]
                tech = entry.get("tech") or ""
                desc = entry["desc"]
                if tech:
                    markdown += f"**{title}** | *{tech}*  \n"
                else:
                    markdown += f"**{title}**  \n"
                if desc:
                    markdown += f"{desc}\n\n"
                else:
                    markdown += "\n"

        if sections["Certifications"]:
            markdown += "## CERTIFICATIONS & BADGES\n"
            for cert in sections["Certifications"]:
                clean_cert = cert.lstrip(" \t\n\r-*•·▪►").strip()
                if clean_cert:
                    markdown += f"* {clean_cert}\n"
        template_clean = (template or "modern").lower().strip()
        return f'<div class="resume-sheet template-{template_clean}">\n' + markdown.strip() + '\n</div>'
    except Exception as e:
        import sys
        print(f"[Offline] Failed to generate tailored resume: {e}", file=sys.stderr)
        raise Exception(f"Failed to generate tailored resume: {e}")


def _escape_latex(text: str) -> str:
    """Escapes special LaTeX characters in a string."""
    chars = {
        '&': r'\&', '%': r'\%', '$': r'\$', '#': r'\#', '_': r'\_',
        '{': r'\{', '}': r'\}', '~': r'\textasciitilde{}', '^': r'\textasciicircum{}',
        '\\': r'\textbackslash{}', '<': r'\textless{}', '>': r'\textgreater{}',
        '–': '--', '—': '---'
    }
    return ''.join(chars.get(c, c) for c in text)


def generate_tailored_resume_latex(resume_text: str, job_text: str, short_bio: str = "", pref_title: str = "", pref_loc: str = "", extra_missing_skills: list = None, template: str = "modern") -> str:
    """
    Generate a tailored resume formatted as LaTeX matching the exact template layout.
    Supports templates: 'modern', 'classic', 'compact'.
    """
    try:
        import re
        resume_skills_data = extract_skills(resume_text)
        job_skills_data = extract_skills(job_text)
        result = match_skills(resume_skills_data, job_skills_data, threshold=0.72)
        
        sections = _parse_resume_sections(resume_text)
        name = _escape_latex(_extract_name(resume_text, sections.get("Header", [])))
        
        loc = _escape_latex(_extract_location(resume_text, pref_loc))
        ext_email, ext_phone, ext_linkedin, ext_github, ext_leetcode = _extract_contacts(resume_text)
        
        email = _escape_latex(ext_email) if ext_email else ""
        phone = _escape_latex(ext_phone) if ext_phone else ""
        linkedin = _escape_latex(ext_linkedin) if ext_linkedin else ""
        github = _escape_latex(ext_github) if ext_github else ""
        leetcode = _escape_latex(ext_leetcode) if ext_leetcode else ""

        row1_latex = []
        if loc: row1_latex.append(loc)
        if phone: row1_latex.append(phone)
        if email: row1_latex.append(r"\href{mailto:" + email + r"}{" + email + r"}")

        row2_latex = []
        if linkedin: row2_latex.append(r"\href{https://" + linkedin + r"}{" + linkedin + r"}")
        if github: row2_latex.append(r"\href{https://" + github + r"}{" + github + r"}")
        if leetcode: row2_latex.append(r"\href{https://" + leetcode + r"}{" + leetcode + r"}")

        latex_sep = r" \quad $|$ \quad "
        total_text_len = len(loc) + len(phone) + len(email) + len(linkedin) + len(github) + len(leetcode)
        if len(row1_latex) + len(row2_latex) <= 3 and total_text_len <= 70 and not github:
            all_latex = row1_latex + row2_latex
            contact_line = latex_sep.join(all_latex) if all_latex else "email@example.com"
        else:
            rows_latex = []
            if row1_latex:
                rows_latex.append(latex_sep.join(row1_latex))
            if row2_latex:
                rows_latex.append(latex_sep.join(row2_latex))
            contact_line = (r" \\" + "\n").join(rows_latex) if rows_latex else "email@example.com"

        # Summary (concise max 1.5 - 2 lines)
        extracted_obj = " ".join(sections.get("Objective", [])).strip()
        bio = _escape_latex(_format_summary(short_bio, extracted_obj))

        # Ensure all missing skills from job description, match results, and extra inputs are included
        resume_skill_set = set()
        for s in (resume_skills_data or []):
            if isinstance(s, dict):
                s_name = (s.get("skill") or s.get("name") or "").strip().lower()
            else:
                s_name = str(s).strip().lower()
            if s_name:
                resume_skill_set.add(s_name)
                canon = ALIASES.get(s_name, s_name).lower()
                resume_skill_set.add(canon)
                for k, v in ALIASES.items():
                    if v.lower() == s_name or v.lower() == canon:
                        resume_skill_set.add(k.lower())

        all_missing_skills = []
        for s in (job_skills_data or []):
            if isinstance(s, dict):
                val = (s.get("skill") or s.get("name") or "").strip().lower()
                if val and val not in resume_skill_set and ALIASES.get(val, "") not in resume_skill_set:
                    all_missing_skills.append(s)
            elif isinstance(s, str) and s.strip():
                val = s.strip().lower()
                if val and val not in resume_skill_set and ALIASES.get(val, "") not in resume_skill_set:
                    all_missing_skills.append({"skill": s.strip(), "category": TECH_SKILLS.get(val, "General")})

        extra_list = []
        if extra_missing_skills:
            for em in extra_missing_skills:
                if isinstance(em, dict):
                    s_name = (em.get("skill") or em.get("name") or "").strip()
                    if s_name:
                        cat = em.get("category") or TECH_SKILLS.get(s_name.lower(), "General")
                        extra_list.append({"skill": s_name, "category": cat})
                elif isinstance(em, str) and em.strip():
                    em_str = em.strip()
                    cat = TECH_SKILLS.get(em_str.lower(), "General")
                    extra_list.append({"skill": em_str, "category": cat})

        missing_pool = []
        seen_missing = set()
        for s in (result.get("missingSkills", []) + all_missing_skills + extra_list):
            if isinstance(s, dict):
                s_name = (s.get("skill") or s.get("name") or "").strip()
                s_low = s_name.lower()
                canon = ALIASES.get(s_low, s_low).lower()
                if s_low and s_low not in seen_missing and canon not in seen_missing:
                    seen_missing.add(s_low)
                    seen_missing.add(canon)
                    cat = s.get("category") or TECH_SKILLS.get(canon, TECH_SKILLS.get(s_low, "General"))
                    missing_pool.append({"skill": s_name, "category": cat})
            elif isinstance(s, str) and s.strip():
                s_str = s.strip()
                s_low = s_str.lower()
                canon = ALIASES.get(s_low, s_low).lower()
                if s_low and s_low not in seen_missing and canon not in seen_missing:
                    seen_missing.add(s_low)
                    seen_missing.add(canon)
                    cat = TECH_SKILLS.get(canon, TECH_SKILLS.get(s_low, "General"))
                    missing_pool.append({"skill": s_str, "category": cat})

        # Skills categorization
        tech_cats, soft_skills = _categorize_skills(resume_skills_data, missing_pool)
        skills_table_latex = ""
        for cat, s_list in tech_cats.items():
            if s_list:
                formatted_latex_skills = []
                for s in s_list:
                    s_name = s["name"] if isinstance(s, dict) else str(s)
                    is_missing = s.get("is_missing", False) if isinstance(s, dict) else False
                    escaped_name = _escape_latex(s_name)
                    if is_missing:
                        formatted_latex_skills.append(r"\textcolor{red}{" + escaped_name + r"}")
                    else:
                        formatted_latex_skills.append(escaped_name)
                s_str = ", ".join(formatted_latex_skills)
                cat_label = _escape_latex(cat)
                skills_table_latex += r"\textbf{" + cat_label + r":} & " + s_str + r" \\" + "\n"

        if soft_skills:
            formatted_latex_soft = []
            for s in soft_skills:
                s_name = s["name"] if isinstance(s, dict) else str(s)
                is_missing = s.get("is_missing", False) if isinstance(s, dict) else False
                escaped_name = _escape_latex(s_name)
                if is_missing:
                    formatted_latex_soft.append(r"\textcolor{red}{" + escaped_name + r"}")
                else:
                    formatted_latex_soft.append(escaped_name)
            soft_str_latex = ", ".join(formatted_latex_soft)
            skills_table_latex += r"\textbf{Soft Skills:} & " + soft_str_latex + r" \\" + "\n"

        soft_skills_latex = ""

        # Education
        edu_latex = ""
        if sections["Education"]:
            parsed_edu = _get_parsed_education_rows(sections["Education"])
            edu_rows_latex = []
            for deg_v, inst_v, yr_v, gr_v in parsed_edu:
                deg_esc = _escape_latex(deg_v) if deg_v else "-"
                inst_esc = _escape_latex(inst_v) if inst_v else "-"
                yr_esc = _escape_latex(yr_v) if yr_v else "-"
                gr_esc = _escape_latex(gr_v) if gr_v else "-"
                edu_rows_latex.append(
                    r"\textbf{" + deg_esc + r"} & " + inst_esc + r" & " + yr_esc + r" & " + gr_esc + r" \\ \hline"
                )
            if edu_rows_latex:
                edu_latex = (
                    r"{\small" + "\n"
                    r"\renewcommand{\arraystretch}{1.18}" + "\n"
                    r"\noindent\begin{tabularx}{\textwidth}{|p{1.7in}|X|c|c|}" + "\n"
                    r"\hline" + "\n"
                    r"\textbf{Course / Degree} & \textbf{Institution / University} & \textbf{Year of Passing} & \textbf{Percentage / CGPA} \\ \hline" + "\n"
                    + "\n".join(edu_rows_latex) + "\n"
                    r"\end{tabularx}" + "\n"
                    r"}\vspace{4pt}" + "\n\n"
                )
            else:
                edu_latex = "N/A\n\n"
        else:
            edu_latex = "N/A\n\n"

        # Projects
        proj_latex = ""
        combined_projects = sections["Projects"]
        if combined_projects:
            proj_entries = _group_project_lines(combined_projects)
            for entry in proj_entries:
                title = _escape_latex(entry["title"])
                tech = _escape_latex(entry.get("tech") or "")
                desc = _escape_latex(entry["desc"])
                
                line1 = r"\noindent \textbf{" + title + r"}"
                if tech:
                    line1 += r" $|$ \textit{" + tech + r"}"
                line1 += r" \\" + "\n"
                
                if desc:
                    proj_latex += line1 + desc + r" \vspace{4pt}" + "\n\n"
                else:
                    proj_latex += line1 + r"\vspace{4pt}" + "\n\n"
        else:
            proj_latex = "N/A\n\n"

        # Certifications
        cert_latex = ""
        if sections["Certifications"]:
            cert_latex += r"\section*{CERTIFICATIONS \& BADGES}" + "\n"
            cert_latex += r"\begin{itemize}[leftmargin=0.2in, itemsep=1pt, topsep=1pt]" + "\n"
            for cert in sections["Certifications"]:
                clean_cert = cert.lstrip(" \t\n\r-*•·▪►").strip()
                if clean_cert:
                    cert_latex += r"    \item " + _escape_latex(clean_cert) + "\n"
            cert_latex += r"\end{itemize}" + "\n\n"

        template_clean = (template or "modern").lower().strip()

        if template_clean == "classic":
            # Classic Executive / Ivy League ATS Template (Traditional Serif typography)
            latex = r"""\documentclass[10pt,a4paper]{article}

\usepackage[
    top=0.45in,
    bottom=0.45in,
    left=0.52in,
    right=0.52in
]{geometry}

\usepackage{mathptmx}
\usepackage{enumitem}
\usepackage[hidelinks]{hyperref}
\usepackage{titlesec}
\usepackage{tabularx}
\usepackage{amssymb}
\usepackage{xcolor}

\setlength{\parindent}{0pt}

\setlist[itemize]{
    leftmargin=0.22in,
    itemsep=1.5pt,
    topsep=1.5pt,
    partopsep=0pt,
    parsep=0pt
}

\titleformat{\section}
{\large\scshape\raggedright}
{}
{0em}
{}
[\titlerule]

\titlespacing{\section}{0pt}{9pt}{4pt}

\begin{document}

% ================= HEADER =================
\begin{center}
{\LARGE \textsc{\textbf{""" + name + r"""}}} \\ \vspace{3pt}
""" + contact_line + r"""
\end{center}

% ================= SUMMARY =================
\section*{Professional Summary}
""" + bio + r"""

% ================= EDUCATION =================
\section*{Education}
""" + edu_latex + r"""
% ================= SKILLS =================
\section*{Core Skills \& Competencies}
\begin{tabular}{@{}p{2.3in}p{4.5in}@{}}
""" + skills_table_latex + r"""\end{tabular}

""" + soft_skills_latex + r"""

% ================= PROJECTS =================
\section*{Key Projects}
""" + proj_latex + r"""
% ================= CERTIFICATIONS =================
""" + cert_latex + r"""
\end{document}"""

        elif template_clean == "compact":
            # Compact 1-Page Minimalist ATS Template (Space-optimized for dense resumes)
            latex = r"""\documentclass[8.5pt,a4paper]{extarticle}

\usepackage[
    top=0.25in,
    bottom=0.25in,
    left=0.36in,
    right=0.36in
]{geometry}

\usepackage{enumitem}
\usepackage[hidelinks]{hyperref}
\usepackage{titlesec}
\usepackage{tabularx}
\usepackage{amssymb}
\usepackage{xcolor}

\setlength{\parindent}{0pt}

\setlist[itemize]{
    leftmargin=0.14in,
    itemsep=0.5pt,
    topsep=0.5pt,
    partopsep=0pt,
    parsep=0pt
}

\titleformat{\section}
{\small\bfseries\uppercase}
{}
{0em}
{}
[\titlerule]

\titlespacing{\section}{0pt}{5pt}{2pt}

\begin{document}

% ================= HEADER =================
\begin{center}
{\large \textbf{""" + name.upper() + r"""}} \\ \vspace{1pt}
{\footnotesize """ + contact_line + r"""}
\end{center}

% ================= SUMMARY =================
\section*{SUMMARY}
{\small """ + bio + r"""}

% ================= EDUCATION =================
\section*{EDUCATION}
{\small """ + edu_latex + r"""}
% ================= SKILLS =================
\section*{TECHNICAL SKILLS}
\small
\begin{tabular}{@{}p{2.2in}p{5.1in}@{}}
""" + skills_table_latex + r"""\end{tabular}

""" + soft_skills_latex + r"""

% ================= PROJECTS =================
\section*{PROJECTS}
{\small """ + proj_latex + r"""}
% ================= CERTIFICATIONS =================
""" + cert_latex + r"""
\end{document}"""

        else:
            # Modern Clean ATS Template (Default)
            latex = r"""\documentclass[9.5pt,a4paper]{extarticle}

\usepackage[
    top=0.35in,
    bottom=0.35in,
    left=0.45in,
    right=0.45in
]{geometry}

\usepackage{enumitem}
\usepackage[hidelinks]{hyperref}
\usepackage{titlesec}
\usepackage{tabularx}
\usepackage{amssymb}
\usepackage{xcolor}

\setlength{\parindent}{0pt}

\setlist[itemize]{
    leftmargin=0.18in,
    itemsep=1pt,
    topsep=1pt,
    partopsep=0pt,
    parsep=0pt
}

\titleformat{\section}
{\normalsize\bfseries}
{}
{0em}
{}
[\titlerule]

\titlespacing{\section}{0pt}{8pt}{3pt}

\begin{document}

% ================= HEADER =================
\begin{center}
{\Large \textbf{""" + name.upper() + r"""}} \\ \vspace{2pt}
""" + contact_line + r"""
\end{center}

% ================= SUMMARY =================
\section*{PROFESSIONAL SUMMARY}
""" + bio + r"""

% ================= EDUCATION =================
\section*{EDUCATION}
""" + edu_latex + r"""
% ================= SKILLS =================
\section*{TECHNICAL SKILLS}
\begin{tabular}{@{}p{2.3in}p{4.6in}@{}}
""" + skills_table_latex + r"""\end{tabular}

""" + soft_skills_latex + r"""

% ================= PROJECTS =================
\section*{PROJECTS}
""" + proj_latex + r"""
% ================= CERTIFICATIONS =================
""" + cert_latex + r"""
\end{document}"""

        return latex
    except Exception as e:
        import sys
        print(f"[Offline] Failed to generate tailored resume (LaTeX): {e}", file=sys.stderr)
        raise Exception(f"Failed to generate tailored resume (LaTeX): {e}")


def generate_cover_letter(resume_text: str, job_text: str, candidate_name: str = "", company_name: str = "", role_title: str = "") -> dict:
    """
    Generates a personalized, ATS-optimized cover letter aligning candidate's background
    with the target job description.
    """
    import datetime
    
    # 1. Candidate Info
    sections = _parse_resume_sections(resume_text)
    name = candidate_name or _extract_name(resume_text, sections.get("Header", []))
    email, phone, linkedin, github, _ = _extract_contacts(resume_text)
    
    # 2. Extract Job Role & Company Name
    if not role_title:
        role_match = re.search(r'(?:role|position|title|job title|opening)\s*[:\-–]\s*([A-Za-z0-9\s/&+\-]+)', job_text, re.IGNORECASE)
        if role_match:
            role_title = role_match.group(1).split('\n')[0].strip()
        else:
            first_line = job_text.strip().split('\n')[0].strip()
            first_line_cleaned = re.sub(r'\s+(?:role|position)\s+(?:at|with)\s+.*$', '', first_line, flags=re.IGNORECASE)
            first_line_cleaned = re.sub(r'^(?:looking for|hiring|seeking)\s+(?:an?|the)?\s*', '', first_line_cleaned, flags=re.IGNORECASE)
            if len(first_line_cleaned) < 60 and not first_line_cleaned.startswith('#'):
                role_title = first_line_cleaned
            else:
                role_title = "Target Position"
    
    if not company_name:
        comp_match = re.search(r'(?:at|with|join|company|organization)\s+([A-Z][A-Za-z0-9\s&]+?)(?:\s+as|\s+team|\.|\n|,|$)', job_text)
        company_name = comp_match.group(1).strip() if comp_match else "your esteemed organization"
    
    # 3. Match Skills
    resume_skills = extract_skills(resume_text)
    job_skills = extract_skills(job_text)
    matched = match_skills(resume_skills, job_skills)
    
    matching_skill_names = [m.get("skill") if isinstance(m, dict) else str(m) for m in (matched.get("matchingSkills") or matched.get("matches") or [])]
    if not matching_skill_names:
        matching_skill_names = [s.get("skill") if isinstance(s, dict) else str(s) for s in resume_skills[:5]]
    
    # Apply proper casing
    cased_skills = []
    for s in matching_skill_names:
        if s:
            s_str = str(s).strip()
            low = s_str.lower()
            if low in ALIASES:
                cased_skills.append(ALIASES[low])
            elif len(s_str) <= 4 and s_str.isupper():
                cased_skills.append(s_str)
            else:
                cased_skills.append(s_str.title())
    top_skills_str = ", ".join(cased_skills[:5]) if cased_skills else "modern technologies and industry best practices"
    
    # 4. Experience & Projects
    projects = sections.get("Projects", [])
    proj_highlight = ""
    if projects:
        first_proj = projects[0].lstrip("-*•·▪► ").strip()
        if len(first_proj) > 20:
            proj_highlight = f" During my recent work, I spearheaded hands-on initiatives including {first_proj[:120]}."
    
    today_str = datetime.date.today().strftime("%B %d, %Y")
    
    # Format contacts header
    contact_parts = []
    if email: contact_parts.append(email)
    if phone: contact_parts.append(phone)
    if linkedin: contact_parts.append(linkedin)
    contact_line = " | ".join(contact_parts)
    
    letter = f"""{name.upper()}
{contact_line}
{today_str}

Hiring Manager
Recruiting Team
{company_name}

Subject: Application for {role_title} Role

Dear Hiring Team,

I am writing to express my strong enthusiasm for the {role_title} opportunity at {company_name}. Having followed your organization's impactful work and industry leadership, I am eager to contribute my technical foundation, proactive problem-solving abilities, and continuous learning mindset to your high-performing team.

My background aligns closely with the core requirements outlined in the job description, particularly in {top_skills_str}.{proj_highlight} Throughout my professional and academic journey, I have prioritized building reliable solutions, collaborating effectively across cross-functional teams, and rapidly mastering new tools and frameworks to deliver measurable business outcomes.

What excites me most about {company_name} is the opportunity to tackle challenging problems and contribute meaningfully to your team's mission. I thrive in collaborative environments where initiative, accountability, and user-centric execution are valued, and I am confident that my work ethic and technical expertise will allow me to make an immediate, positive impact.

Thank you for your time and consideration. I would welcome the opportunity to discuss further how my skills and background can support the continued growth of {company_name}. I look forward to the possibility of an interview.

Sincerely,

{name}"""
    
    return {
        "candidateName": name,
        "companyName": company_name,
        "roleTitle": role_title,
        "coverLetter": letter.strip()
    }


def generate_cover_letter_latex(cover_letter_text: str) -> str:
    """Formats raw cover letter text into professional LaTeX A4 letter document."""
    paras = [p.strip() for p in cover_letter_text.strip().split('\n\n') if p.strip()]
    
    header_tex = ""
    body_paras = paras
    
    if len(paras) >= 3 and len(paras[0].split('\n')) <= 2:
        top_lines = [l.strip() for l in paras[0].split('\n') if l.strip()]
        name = _escape_latex(top_lines[0])
        contact = _escape_latex(top_lines[1]) if len(top_lines) > 1 else ""
        header_tex = r"""\begin{center}
{\LARGE \textbf{""" + name + r"""}} \\ \vspace{4pt}
{\small """ + contact + r"""}
\end{center} \vspace{8pt} \hrule \vspace{14pt}"""
        body_paras = paras[1:]

    latex_body = []
    for p in body_paras:
        escaped_lines = [_escape_latex(line) for line in p.split('\n')]
        para_text = (r" \\" + "\n").join(escaped_lines)
        latex_body.append(para_text + r" \par \vspace{10pt}")

    body_content = "\n".join(latex_body)

    latex = r"""\documentclass[11pt,a4paper]{article}
\usepackage[
    top=0.7in,
    bottom=0.7in,
    left=0.8in,
    right=0.8in
]{geometry}
\usepackage{mathptmx}
\usepackage[hidelinks]{hyperref}
\usepackage{parskip}

\setlength{\parindent}{0pt}

\begin{document}
""" + header_tex + r"""
""" + body_content + r"""
\end{document}"""
    return latex
