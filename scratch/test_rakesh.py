import sys
import os
import fitz

sys.path.append(os.path.abspath('backend'))
import analyzer

doc = fitz.open('../rakesh resume.pdf')
raw_text = "\n".join([page.get_text("text") for page in doc])

job_text = """
Software Engineer
Requirements: Node.js, Express, MongoDB, JavaScript, Python
"""

# Test sections
sections = analyzer._parse_resume_sections(raw_text)
print("=== Education Section lines in sections['Education'] ===")
for l in sections["Education"]:
    print(repr(l))

print("\n=== Parsed Education Rows via _get_parsed_education_rows ===")
parsed = analyzer._get_parsed_education_rows(sections["Education"])
for i, r in enumerate(parsed):
    print(f"Row {i}: Degree={r[0]!r} | Inst={r[1]!r} | Year={r[2]!r} | Grade={r[3]!r}")

print("\n=== Tailored Resume Markdown Education Section ===")
md = analyzer.generate_tailored_resume(raw_text, job_text, template="modern")
edu_snippet = md[md.find("## EDUCATION"):md.find("## TECHNICAL SKILLS")]
print(edu_snippet)

print("=== Tailored Resume LaTeX Education Section ===")
latex = analyzer.generate_tailored_resume_latex(raw_text, job_text, template="modern")
idx1 = latex.find("Course / Degree")
if idx1 != -1:
    print(latex[idx1-50:idx1+400])

# Verify LaTeX compiles
import subprocess
os.makedirs('backend/temp', exist_ok=True)
tex_file = 'test_rakesh.tex'
with open(os.path.join('backend/temp', tex_file), 'w', encoding='utf-8') as f:
    f.write(latex)
res = subprocess.run(['pdflatex', '-interaction=nonstopmode', tex_file], cwd='backend/temp', stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
print("LaTeX pdflatex returncode:", res.returncode)
assert res.returncode == 0, f"LaTeX failed: {res.stdout[-400:]}"
print("[SUCCESS] All checks and PDF compilation passed for Rakesh resume!")
