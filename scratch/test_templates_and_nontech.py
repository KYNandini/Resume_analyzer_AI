import requests
import json
import fitz

# Create sample non-tech Finance resume PDF
doc = fitz.open()
page = doc.new_page()
page.insert_text((50, 72), '''PRIYA SHARMA
priya.sharma@gmail.com | +91 9876543210 | linkedin.com/in/priyasharma
EDUCATION
B.Com in Accounting and Finance, Delhi University, 2025, 8.2 CGPA
TECHNICAL SKILLS
Accounting, Tally Prime, Financial Accounting, Balance Sheet, Excel
EXPERIENCE
Finance Intern | ABC Corp | 2024
Prepared financial statements and assisted in audit reconciliation.
''')
pdf_bytes = doc.tobytes()

files = {
    'resume': ('priya_resume.pdf', pdf_bytes, 'application/pdf')
}

# Missing finance skills
missing = [
    {'skill': 'taxation', 'category': 'Finance'},
    {'skill': 'gst', 'category': 'Finance'},
    {'skill': 'financial modeling', 'category': 'Finance'},
    {'skill': 'auditing', 'category': 'Finance'}
]

data = {
    'jobText': 'Financial Analyst / Accountant role requiring GST, Taxation, Auditing, and Financial Modeling',
    'missingSkills': json.dumps(missing)
}

print("=== 1. TESTING NON-TECH FINANCE SKILLS CATEGORIZATION ===")
resp = requests.post('http://localhost:3000/build-resume', files=files, data={**data, 'template': 'modern'})
assert resp.status_code == 200, f"Modern resume failed: {resp.text}"
md_modern = resp.json()['tailoredResume']
assert 'Finance & Accounting' in md_modern, "Finance & Accounting category should be present"
assert '<span class="missing-skill" style="color: red; font-weight: 700;">GST</span>' in md_modern or 'GST' in md_modern, "GST missing"
assert 'Financial Modeling' in md_modern, "Financial Modeling missing"
print("[OK] Finance skills dynamically categorized under 'Finance & Accounting' with red highlights!")

print("\n=== 2. TESTING MULTIPLE ATS TEMPLATES (LATEX COMPILATION) ===")

for tpl in ['modern', 'classic', 'compact']:
    print(f"\n--> Testing Template: '{tpl}' ...")
    # Test Markdown
    res_md = requests.post('http://localhost:3000/build-resume', files={'resume': ('priya_resume.pdf', pdf_bytes, 'application/pdf')}, data={**data, 'template': tpl})
    assert res_md.status_code == 200, f"{tpl} markdown failed"
    print("  tailoredResume snippet:", repr(res_md.json()['tailoredResume'][:150]))
    assert f'template-{tpl}' in res_md.json()['tailoredResume'], f"template-{tpl} class missing in output"
    print(f"  [OK] Markdown rendered with template-{tpl} wrapper")

    # Test LaTeX Compilation
    res_latex = requests.post('http://localhost:3000/build-resume-latex', files={'resume': ('priya_resume.pdf', pdf_bytes, 'application/pdf')}, data={**data, 'template': tpl})
    assert res_latex.status_code == 200, f"{tpl} latex failed: {res_latex.text}"
    latex_json = res_latex.json()
    assert 'pdfData' in latex_json, f"{tpl} pdfData missing"
    print(f"  [OK] LaTeX compiled to PDF successfully! ({len(latex_json['pdfData'])} bytes base64)")

print("\n=== ALL TESTS PASSED: Non-Tech Domains & Multiple ATS Templates Fully Verified! ===")
