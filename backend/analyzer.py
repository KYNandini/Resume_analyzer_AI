import sys
import json
import spacy
from sentence_transformers import SentenceTransformer, util

# Load models
nlp = spacy.load("en_core_web_sm")
model = SentenceTransformer('all-MiniLM-L6-v2')

resume_text = sys.argv[1]
job_text = sys.argv[2]

resume_doc = nlp(resume_text.lower())
job_doc = nlp(job_text.lower())

# ✅ Custom stop words
CUSTOM_STOP = {
    "experience", "work", "project", "role", "team",
    "developer", "software", "application", "using",
    "knowledge", "skills", "ability",
    "system", "data", "service"
}

from spacy.lang.en.stop_words import STOP_WORDS as SPACY_STOP

# ✅ Extract keywords (lemma based)
def extract_keywords(doc):
    return set([
        token.lemma_.lower()
        for token in doc
        if token.is_alpha
        and len(token.text) > 2
        and token.lemma_.lower() not in CUSTOM_STOP
        and token.lemma_.lower() not in SPACY_STOP
    ])

# Extract
resume_words = list(extract_keywords(resume_doc))
job_words = list(extract_keywords(job_doc))

# 🚨 Safety check
if not resume_words or not job_words:
    print(json.dumps({
        "score": 0,
        "matched": [],
        "missing": job_words,
        "suggestions": ["Add more technical skills"]
    }))
    sys.exit()

# 🔥 Embeddings
resume_embeddings = model.encode(resume_words, convert_to_tensor=True)
job_embeddings = model.encode(job_words, convert_to_tensor=True)

matched = []
missing = []

# 🔥 Semantic matching
for i, job_word in enumerate(job_words):
    similarities = util.cos_sim(job_embeddings[i], resume_embeddings)
    max_score = similarities.max().item()

    if max_score > 0.6:
        matched.append(job_word)
    else:
        missing.append(job_word)

matched = sorted(matched)
missing = sorted(missing)

# 🔥 Score
score = int((len(matched) / len(job_words)) * 100) if job_words else 0

# 🔥 Suggestions
suggestions = [f"Learn {skill}" for skill in missing[:5]]

# 🔥 Output
result = {
    "score": score,
    "matched": matched[:10],
    "missing": missing[:10],
    "suggestions": suggestions
}

print(json.dumps(result))