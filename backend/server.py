from flask import Flask, request, jsonify
from flask_cors import CORS
import spacy
import fitz  # PyMuPDF

app = Flask(__name__)
CORS(app)

nlp = spacy.load("en_core_web_sm")

from spacy.lang.en.stop_words import STOP_WORDS as SPACY_STOP

CUSTOM_STOP = {
    "experience", "work", "project", "role",
    "developer", "software", "application", "using",
    "knowledge", "skills", "ability",
    "system", "data", "service"
}

def extract_keywords(doc):
    return set([
        token.lemma_.lower()
        for token in doc
        if token.is_alpha
        and len(token.text) > 2
        and token.pos_ in ["NOUN", "PROPN"]
        and token.lemma_.lower() not in CUSTOM_STOP
        and token.lemma_.lower() not in SPACY_STOP
    ])

def extract_text_from_pdf(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text

@app.route("/analyze", methods=["POST"])
def analyze():
    resume_file = request.files.get("resume")
    job_text = request.form.get("jobText", "")

    if not resume_file or not job_text:
        return jsonify({"error": "Resume and job description are required"}), 400

    try:
        resume_text = extract_text_from_pdf(resume_file)
    except:
        return jsonify({"error": "Invalid PDF file"}), 400

    resume_doc = nlp(resume_text.lower())
    job_doc = nlp(job_text.lower())

    resume_words = list(extract_keywords(resume_doc))
    job_words = list(extract_keywords(job_doc))

    # remove duplicates
    resume_words = list(set(resume_words))
    job_words = list(set(job_words))

    if not resume_words:
        return jsonify({
            "matchPercent": 0,
            "missingPercent": 100,
            "efficiencyPercent": 10,
            "matchingSkills": [],
            "missingSkills": job_words[:10],
            "totalSkills": len(job_words),
            "matchedCount": 0,
            "suggestions": {}
        })

    if not job_words:
        job_words = list(set([
            token.lemma_.lower()
            for token in job_doc
            if token.is_alpha and token.pos_ in ["NOUN", "PROPN"]
        ]))

    if not job_words:
        return jsonify({
            "matchPercent": 0,
            "missingPercent": 100,
            "efficiencyPercent": 10,
            "matchingSkills": [],
            "missingSkills": [],
            "totalSkills": 0,
            "matchedCount": 0,
            "suggestions": {}
        })

    # 🔥 FAST MATCHING (NO AI MODEL → NO FREEZE)
    matched = sorted(list(set(resume_words) & set(job_words)))
    missing = sorted(list(set(job_words) - set(resume_words)))

    match_percent = int((len(matched) / len(job_words)) * 100)

    result = {
        "matchPercent": match_percent,
        "missingPercent": 100 - match_percent,
        "efficiencyPercent": min(match_percent + 10, 100),
        "matchingSkills": matched[:8],
        "missingSkills": missing[:8],
        "totalSkills": len(job_words),
        "matchedCount": len(matched),
        "suggestions": {
            skill: f"Add projects related to {skill}"
            for skill in missing[:5]
        }
    }

    return jsonify(result)

if __name__ == "__main__":
    app.run(port=3000, debug=True)