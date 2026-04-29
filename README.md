# 📄 Resume Analyzer AI

An intelligent web application that helps candidates align their resumes with job descriptions. The tool uses Natural Language Processing (NLP) to analyze your resume against a target job description and provides actionable insights, such as match percentage, missing skills, and suggestions for improvement.

## ✨ Features

- **User Authentication:** Simple login and registration system.
- **PDF Resume Parsing:** Extracts text and skills seamlessly from uploaded PDF resumes.
- **Smart Keyword Matching:** Leverages NLP (spaCy) to identify and compare technical skills and keywords from both the resume and the job description.
- **Detailed Insights Dashboard:**
  - Match & Missing Percentages
  - Matched Skills & Missing Skills
  - Actionable Suggestions to improve your resume.
- **Fast & Responsive UI:** Clean, modern, and interactive interface built with HTML, CSS, and Vanilla JavaScript.

## 🛠️ Tech Stack

- **Frontend:** HTML5, CSS3, Vanilla JavaScript
- **Backend:** Python, Flask
- **Machine Learning / NLP:** spaCy (`en_core_web_sm`)
- **PDF Parsing:** PyMuPDF (`fitz`)

## 🚀 Getting Started

Follow these steps to run the application locally on your machine.

### Prerequisites

- **Python 3.13** (Note: spaCy is currently incompatible with Python 3.14 due to pydantic versioning)
- A modern Web Browser (Chrome, Firefox, Edge, Safari)

### 1. Set Up the Backend

1. Open your terminal and navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Install the required Python dependencies:
   ```bash
   pip install flask flask-cors spacy pymupdf
   ```
3. Download the necessary spaCy English language model:
   ```bash
   python -m spacy download en_core_web_sm
   ```
4. Start the Flask server:
   ```bash
   python server.py
   ```
   *The backend should now be running locally on `http://127.0.0.1:3000`*

### 2. Run the Frontend

The frontend consists of static HTML files, so you don't need a dedicated web server to run them.

1. Navigate to the root directory of the project in your File Explorer.
2. Go into the `resume-analyzer-login` folder.
3. Open `index.html` directly in your web browser.
4. Create an account, log in, and you will be redirected to the Analysis Dashboard to start analyzing resumes!

## 📂 Project Structure

```text
Resume_Analyzer_AI/
├── backend/
│   ├── analyzer.py        # Additional Sentence Transformer Logic
│   ├── server.py          # Main Flask Backend Server (Primary)
│   └── server.js          # Express Alternative Backend Server
├── resume-analyzer-login/ # Login and Registration UI
│   ├── index.html
│   ├── script.js
│   └── style.css
├── analysis-dashboard/    # Main Application Dashboard UI
│   ├── index.html
│   └── style.css
└── README.md              # Project Documentation
```
