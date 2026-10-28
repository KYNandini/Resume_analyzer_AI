import sys
import os

sys.path.append(os.path.abspath('backend'))
import analyzer

layout_a = """RESUME
NAME: Basamma
EMAIL ID: Basammarajapur82@gmail.com
MOBILE NO. 7676136892

OBJECTIVE
To server the Organization or institution with which I associates at any point of point of time with best of my knowledge and to keep on learning new concepts from which I can deliver I can deliver my best work

EDUCATIONAL QUALIFICATION
EDUCATIONAL QUALIFICATION
DEGREE/ STREAM / SPECIALIZATION
NAME OF THE EDUCATIONAL INSTITUTION / UNIVERSITY
YEAR OF PASSING
CGPA / PERCENTAGE / GRADE
10th STD / SSLC
State
Gangadhar bakka prabhu high school Gulbarga
2022
84.96%
Diploma
Computer science and engineering
Government polytechnic for women's kalaburagi
2025

SOFT SKILLS
Team worker, time management, active listening skill, leadership

TECHNICAL SKILLS
java, python, DBMS, OS with Linux , networking , AWS , cyber security
"""

job_desc = "Software Engineer: Python, Java, AWS, Microservices"

sections = analyzer._parse_resume_sections(layout_a)
print("=== LAYOUT A SECTIONS ===")
for k, v in sections.items():
    if v:
        print(f"[{k}] ({len(v)} lines):", v)

parsed = analyzer._get_parsed_education_rows(sections["Education"])
print("\nParsed edu rows count:", len(parsed))
for r in parsed:
    print(r)

md = analyzer.generate_tailored_resume(layout_a, job_desc)
print("\n=== MARKDOWN TAILORED RESUME ===")
print(md[:600])
