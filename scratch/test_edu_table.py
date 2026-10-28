import sys
import os
import subprocess
import requests
import json
import fitz

sys.path.append(os.path.abspath('backend'))
from analyzer import generate_tailored_resume, generate_tailored_resume_latex

sample_resume = '''
ROHAN VERMA
rohan.verma@email.com | +91 9876543210 | Bangalore, India | linkedin.com/in/rohanverma

EDUCATION
B.Tech in Computer Science and Engineering
R.V. College of Engineering, Bangalore
2020 - 2024
8.8 CGPA

Higher Secondary (12th), Delhi Public School, 2020, 95.2 percentile

TECHNICAL SKILLS
Python, JavaScript, React, SQL, Docker

PROJECTS
Smart Health AI | Python, PyTorch
Developed an automated diagnosis assistance tool.
'''

job_text = '''
Full Stack Engineer
Required: Python, React, JavaScript, Kubernetes, AWS
'''

# 1. Test HTML / Markdown generation
md = generate_tailored_resume(sample_resume, job_text, template='modern')
print("=== MARKDOWN EDUCATION SECTION ===")
edu_snippet = md[md.find("## EDUCATION"):md.find("## TECHNICAL SKILLS")]
print(edu_snippet)

assert 'education-table' in md, 'education-table class missing'
assert 'Course / Degree' in md, 'Course / Degree header missing'
assert 'Institution / University' in md, 'Institution / University header missing'
assert 'Year of Passing' in md, 'Year of Passing header missing'
assert 'Percentile / CGPA' in md, 'Percentile / CGPA header missing'
assert 'R.V. College of Engineering' in md, 'College name missing'
assert 'CGPA: 8.8' in md or '8.8 CGPA' in md, 'CGPA missing'
assert 'Percentile: 95.2' in md, 'Percentile missing'
print("[PASS] Markdown Education table generated with all requested columns and values!")

# 2. Test LaTeX compilation across modern, classic, compact
os.makedirs('backend/temp', exist_ok=True)
for tpl in ['modern', 'classic', 'compact']:
    tex = generate_tailored_resume_latex(sample_resume, job_text, template=tpl)
    assert 'tabularx' in tex, f'{tpl}: tabularx missing'
    assert 'Course / Degree' in tex, f'{tpl}: Course / Degree header missing'
    assert 'Institution / University' in tex, f'{tpl}: Institution / University header missing'
    assert 'Year of Passing' in tex, f'{tpl}: Year of Passing header missing'
    assert 'Percentile / CGPA' in tex, f'{tpl}: Percentile / CGPA header missing'
    
    tex_file = f'test_table_{tpl}.tex'
    with open(os.path.join('backend/temp', tex_file), 'w', encoding='utf-8') as f:
        f.write(tex)
    res = subprocess.run(['pdflatex', '-interaction=nonstopmode', tex_file], cwd='backend/temp', stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert res.returncode == 0, f"pdflatex compilation failed for {tpl}: {res.stdout[-500:]}"
    print(f"[PASS] LaTeX template '{tpl}' compiled to PDF successfully with return code 0!")

print("\n=== ALL DIRECT EDUCATION TABLE TESTS PASSED! ===")
