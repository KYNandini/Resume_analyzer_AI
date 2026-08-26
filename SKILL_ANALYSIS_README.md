# Resume Analyzer AI - Skills Match & NLP Engine Guide

This document provides a technical explanation of how the backend extracts, processes, and matches skills between a user's resume and a target job description. The logic for this engine is contained entirely within `backend/analyzer.py`.

## Core Technologies
The skill extraction and matching engine is built to be robust, utilizing a layered approach that combines deterministic dictionary lookups with advanced Machine Learning NLP models.

- **spaCy (`en_core_web_lg`)**: Used for Named Entity Recognition (NER) and noun-chunk phrase extraction.
- **Sentence-Transformers (`all-MiniLM-L6-v2`)**: A lightweight (~80 MB), highly accurate transformer model used to calculate semantic similarity between skills that are phrased differently.
- **Google Gemini API (`gemini-1.5-flash`)**: Used to generate context-aware, personalized improvement suggestions for missing skills.

---

## 1. Skill Extraction Process

When a resume PDF is uploaded, the text is extracted using `PyMuPDF (fitz)`. The raw text of both the resume and the job description undergoes a **Two-Pass Extraction Process**:

### Pass 1: Curated Vocabulary Scan (Deterministic)
The system maintains a large, curated dictionary of over 700 standard technical and soft skills (`TECH_SKILLS`), categorized into domains like "Cloud", "DevOps", "AI/ML", etc.
- **Normalization**: The raw text is stripped of special characters, converted to lowercase, and normalized using an aliases dictionary (e.g., converting "react.js" to "react", or "k8s" to "kubernetes").
- **Longest Match First**: To prevent partial false-positives (e.g., matching "react" inside "react native"), the dictionary is sorted by phrase length.
- **Ambiguity Handling**: Specific skills that overlap with common English words (like "C", "R", "Go", "Rest") are strictly evaluated using case-sensitive boundaries.

### Pass 2: spaCy NLP Fallback (Probabilistic)
If `spaCy` is successfully loaded, the text is fed into the `en_core_web_lg` model. 
- The model extracts continuous **noun chunks** and **named entities** (like ORG or PRODUCT). 
- If a detected entity matches a known skill but was missed by the exact phrase matching in Pass 1, it is appended to the extracted skills list.

---

## 2. Skill Matching & Scoring Engine

Once both the resume and the job description are converted into arrays of extracted skills, the engine determines the overlap. This is also a layered approach:

### Pass 1: Exact Matching
The engine first performs a direct intersection of the normalized skill sets. If a job requires "Python" and the resume contains "Python", it is immediately categorized as a **100% Exact Match**.

### Pass 2: Semantic Similarity (SBERT)
Often, job descriptions and resumes use different terminology for the same underlying skill (e.g., "Machine Learning" vs "ML", or "GCP" vs "Google Cloud").
- The engine uses the `all-MiniLM-L6-v2` transformer model to encode the remaining unmatched job skills and the resume skills into high-dimensional vector embeddings.
- It then calculates the **Cosine Similarity** between these vectors. 
- If the similarity score exceeds the strict threshold of **0.72**, it is registered as a **Semantic Match**.

### Fallback: Jaccard Similarity
If the host machine is unable to load the heavy transformer models, the system gracefully degrades to using character-level **Jaccard Similarity**. It splits the phrases into sets and calculates the overlap ratio, requiring a threshold of 0.3 to match.

---

## 3. Prioritization & AI Suggestions

Skills found in the job description but completely missing from the resume (failing both exact and semantic matches) are moved to the `missingSkills` array.

- **Priority Tagging**: Missing skills are assigned a priority. If a missing skill had a very low semantic similarity to anything on the resume (score < 0.4), it is flagged as **High Priority**.
- **Gemini AI Integration**: The array of missing skills, along with a 300-character context snippet of the job description, is sent to the Google Gemini API. Gemini acts as a career coach, returning a customized 1-2 sentence tip on how the user can acquire and demonstrate that specific skill for that specific job context.
- **Static Fallbacks**: If the Gemini API key is missing or the API fails, the system falls back to a massive dictionary of hand-written, category-specific suggestions (e.g., recommending a Coursera certification for missing AI/ML skills).

## 4. Final Score Calculation
The final ATS Match Score is a simple ratio: `(Total Matched Skills / Total Job Skills) * 100`. The engine then provides overarching feedback based on whether the score falls into the Excellent (>80%), Good (>60%), Fair (>40%), or Needs Improvement brackets.
