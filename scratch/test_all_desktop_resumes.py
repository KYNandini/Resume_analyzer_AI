import os
import glob
import fitz # PyMuPDF
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from backend.analyzer import _parse_resume_sections, _get_parsed_education_rows, generate_tailored_resume

def test_all():
    desktop_resumes = glob.glob(r"C:\Users\nandi\Desktop\Resumes\*.pdf")
    print(f"Found {len(desktop_resumes)} resumes in C:\\Users\\nandi\\Desktop\\Resumes")

    for pdf_path in sorted(desktop_resumes):
        name = os.path.basename(pdf_path)
        try:
            doc = fitz.open(pdf_path)
            text = "\n".join(page.get_text() for page in doc)
            doc.close()

            sections = _parse_resume_sections(text)
            edu_lines = sections.get("Education", [])
            parsed_rows = _get_parsed_education_rows(edu_lines)

            print("=" * 80)
            print(f"RESUME: {name}")
            print(f"RAW EDU LINES COUNT: {len(edu_lines)}")
            print("PARSED EDUCATION ROWS:")
            for row in parsed_rows:
                print(f"  - Course/Degree: '{row[0]}'")
                print(f"    Institution:   '{row[1]}'")
                print(f"    Year:          '{row[2]}'")
                print(f"    Percentage:    '{row[3]}'")

            # Also verify generate_tailored_resume works without error
            job_text = "Looking for software engineer with Python, Java, React, SQL."
            tailored = generate_tailored_resume(text, job_text)
            assert "<table class=\"education-table\"" in tailored or len(parsed_rows) == 0
            assert "Percentage / CGPA" in tailored or len(parsed_rows) == 0

        except Exception as e:
            print(f"ERROR on {name}: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_all()
