import sys
import os
import re

sys.path.append(os.path.abspath('backend'))
import analyzer

# Test with Secondary Education in degree patterns
old_is_deg = analyzer._is_degree_kw
def new_is_deg(text):
    t = text.lower()
    if re.search(r'\b(?:secondary\s+education|higher\s+secondary\s+education|senior\s+secondary\s+education|primary\s+education)\b', t):
        return True
    return old_is_deg(text)

analyzer._is_degree_kw = new_is_deg

edu_lines = [
    'Bachelor of Engineering in Computer Science',
    'Government Engineering College, Mosalehosahalli, Hassan',
    'CGPA: 7.75 / 10',
    'Pre-University \u2013',
    '2023',
    'M S PU College, Honnali, Davangere',
    'Percentage: 73.44%',
    'Secondary Education \u2013',
    '2021',
    'Jnana Ganga English Medium School, Kundur, Davangere',
    'Percentage: 90.72%'
]

entries = analyzer._group_education_lines(edu_lines)
print("Entries count:", len(entries))
for i, e in enumerate(entries):
    print(f"Entry {i}:", e)
