import sys
import os
import subprocess
from pymongo import MongoClient

sys.path.append(os.path.abspath('backend'))
from server import extract_text_from_pdf
from analyzer import generate_tailored_resume, generate_tailored_resume_latex

client = MongoClient('mongodb://localhost:27017/')
db = client['resumeanalyzer']
doc = db['resumes'].find_one({'filename': 'Resume 4.pdf'})

print("Extracting text from Resume 4.pdf...")
resume_text = extract_text_from_pdf(doc['file_data'])

job_text = """
Full Stack Web Developer
Required: Python, Java, AWS, DBMS, Linux, Microservices, Node.js
"""

print("\n--- 1. Testing Tailored Resume HTML / Markdown ---")
md = generate_tailored_resume(resume_text, job_text, template="modern")

# Verify candidate name is Basamma (not CANDIDATE NAME, not RESUME)
assert "BASAMMA" in md, f"Expected BASAMMA in markdown name, got: {md[:300]}"
assert "Basammarajapur82@gmail.com" in md, "Expected email in markdown"
assert "7676136892" in md, "Expected phone in markdown"
assert "N/A" not in md[md.find("## EDUCATION"):md.find("## TECHNICAL SKILLS")], "Education should not be N/A!"
assert "10th" in md or "SSLC" in md, "Expected SSLC in education"
assert "Diploma" in md, "Expected Diploma in education"

print("[PASS] Markdown tailored resume successfully generated with candidate name, contact, and education table!")
edu_snippet = md[md.find("## EDUCATION"):md.find("## TECHNICAL SKILLS")]
print("\n" + edu_snippet)

print("\n--- 2. Testing Tailored Resume LaTeX Compilation ---")
os.makedirs('backend/temp', exist_ok=True)
for tpl in ['modern', 'classic', 'compact']:
    tex = generate_tailored_resume_latex(resume_text, job_text, template=tpl)
    assert "Basamma" in tex, f"Expected Basamma in {tpl} LaTeX"
    assert "Gangadhar" in tex, f"Expected School in {tpl} LaTeX"
    assert "Diploma" in tex, f"Expected Diploma in {tpl} LaTeX"
    
    tex_file = f"test_basamma_{tpl}.tex"
    with open(os.path.join('backend/temp', tex_file), 'w', encoding='utf-8') as f:
        f.write(tex)
    res = subprocess.run(['pdflatex', '-interaction=nonstopmode', tex_file], cwd='backend/temp', stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert res.returncode == 0, f"LaTeX {tpl} failed: {res.stdout[-300:]}"
    print(f"[PASS] Template {tpl} compiled successfully with return code 0!")

print("\n=== ALL TESTS PASSED: Resume 4.pdf (Basamma) fully supported and verified! ===")
