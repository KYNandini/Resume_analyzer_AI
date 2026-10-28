import sys
import os
import re

sys.path.append(os.path.abspath('backend'))
import analyzer

# Transcribed text from the user's uploaded image:
basamma_resume = """RESUME
NAME: Basamma
EMAIL ID: Basammarajapur82@gmail.com
MOBILE NO. 7676136892

OBJECTIVE
To server the Organization or institution with which I associates at any point of point of time with best of my knowledge and to keep on learning new concepts from which I can deliver I can deliver my best work

EDUCATIONAL QUALIFICATION
EDUCATIONAL QUALIFICATION | DEGREE/ STREAM / SPECIALIZATION | NAME OF THE EDUCATIONAL INSTITUTION / UNIVERSITY | YEAR OF PASSING | CGPA / PERCENTAGE / GRADE
10th STD / SSLC | State | Gangadhar bakka prabhu high school Gulbarga | 2022 | 84.96%
Diploma | Computer science and engineering | Government polytechnic for women's kalaburagi | 2025 | 

SOFT SKILLS
Team worker, time management, active listening skill, leadership

TECHNICAL SKILLS
java, python, DBMS, OS with Linux , networking , AWS , cyber security

APPRENTICESHIP / INTERNSHIP
Name of the Company / Organization | Apprenticeship / Internship Role / Title | Roles and Responsibility and projects worked on. | Total Duration (Eg: - 1 Year 2 Months)
Providence | | Linux, java, python | 3 months

PERSONAL DETAILS
NAME: Basamma
DOB: 26-1-2007
GENDER: female
LANGUAGES KNOWN TO SPEAK: Kannada, English, Hindi
LANGUAGES KNOWN TO READ: Kannada ,English Hindi
HOBBIES: Listening music, reading stories
ADDRESS: Basava Nagar kudhalli 585324
"I certify that the information provided in this resume is true and accurate to the best of my knowledge."
DATE:
PLACE:
"""

sections = analyzer._parse_resume_sections(basamma_resume)
print("=== SECTIONS ===")
for k, v in sections.items():
    print(f"[{k}] ({len(v)} lines):", v)

name = sections["Header"][0] if sections["Header"] else "Candidate Name"
print("\nExtracted Name:", name)

email, phone, linkedin, github, leetcode = analyzer._extract_contacts(basamma_resume)
print("Extracted Contacts:", f"email={email}, phone={phone}, linkedin={linkedin}")

print("\n=== EDUCATION ENTRIES ===")
parsed_edu = analyzer._get_parsed_education_rows(sections["Education"])
print("Parsed edu count:", len(parsed_edu))
for r in parsed_edu:
    print(r)
