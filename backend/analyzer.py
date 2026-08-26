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
from typing import Optional
from dotenv import load_dotenv

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
    "linux": "DevOps", "unix": "DevOps", "git": "DevOps",
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
    "postman": "Testing", "tdd": "Testing", "bdd": "Testing",
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
    missing_pct = 100 - match_pct
    eff_pct = min(match_pct + 8, 100)

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
        "matchingSkills": matched_skills[:20],
        "missingSkills": missing_skills[:20],
        "totalSkills": total,
        "matchedCount": match_count,
        "categoryBreakdown": category_stats,
    }


def _empty_result(job_skills: list[dict] = None) -> dict:
    missing = job_skills[:20] if job_skills else []
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
# Gemini AI Suggestions
# ---------------------------------------------------------------------------
def get_gemini_suggestions(missing_skills: list[dict], job_context: str) -> dict[str, str]:
    """
    Generate AI-powered improvement suggestions for each missing skill.
    Falls back to curated static suggestions if API key not set.
    """
    api_key = os.getenv("GEMINI_API_KEY", "")
    skill_names = [s["skill"] for s in missing_skills[:8]]

    if not api_key or not skill_names:
        return {s: _static_suggestion(s) for s in skill_names}

    try:
        import importlib
        genai_mod = importlib.import_module("google.genai")
        client = genai_mod.Client(api_key=api_key)

        prompt = (
            f"You are a career coach. For each skill below, give a concise, actionable 1-2 sentence "
            f"improvement tip for a job seeker targeting: '{job_context[:200]}'. "
            f"Output ONLY a JSON object mapping each skill name to its tip. Skills: {skill_names}"
        )
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt
        )
        text = response.text.strip()
        # Extract JSON from response
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            import json
            suggestions = json.loads(json_match.group())
            return {k.lower(): v for k, v in suggestions.items()}
    except Exception as e:
        import sys
        print(f"[Gemini] Falling back to static suggestions: {e}", file=sys.stderr)

    return {s: _static_suggestion(s) for s in skill_names}


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

if __name__ == "__main__":
    import sys
    import json
    
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Missing arguments"}))
        sys.exit(1)
        
    resume_path = sys.argv[1]
    job_path = sys.argv[2]
    
    try:
        with open(resume_path, "r", encoding="utf-8") as f:
            resume_text = f.read()
        with open(job_path, "r", encoding="utf-8") as f:
            job_text = f.read()
            
        resume_skills = extract_skills(resume_text)
        job_skills = extract_skills(job_text)
        
        result = match_skills(resume_skills, job_skills, threshold=0.72)
        
        job_context = job_text[:300]
        suggestions = get_gemini_suggestions(result["missingSkills"], job_context)
        
        for skill_obj in result["missingSkills"]:
            skill_name = skill_obj["skill"]
            skill_obj["suggestion"] = suggestions.get(skill_name, suggestions.get(skill_name.lower(), f"Research and add {skill_name} to your skill set."))
            
        result["suggestions"] = {
            s["skill"]: s.get("suggestion", "") for s in result["missingSkills"]
        }
        
        match_pct = result.get("matchPercent", 0)
        if match_pct >= 80:
            result["overallFeedback"] = "Excellent match! Your resume is ATS-optimized and closely aligned to this role."
        elif match_pct >= 60:
            result["overallFeedback"] = "Good alignment. Adding a few missing skills will significantly boost your ATS score."
        elif match_pct >= 40:
            result["overallFeedback"] = "Fair match. Focus on the high-priority missing skills to strengthen your application."
        else:
            result["overallFeedback"] = "Your resume needs targeted improvements. Prioritize the missing skills listed below."
            
        print(json.dumps(result))
    except Exception as e:
        import traceback
        print(json.dumps({"error": str(e), "trace": traceback.format_exc()}))