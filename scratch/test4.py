import sys
sys.path.append('backend')
from analyzer import extract_skills

langs = ["Python, Java, SQL, JavaScript, Kannada (Native), English (Professional), Hindi (Fluent)"]

clean_langs = []
for lang_line in langs:
    parts = [p.strip() for p in lang_line.split(',')]
    valid_parts = []
    for p in parts:
        skills_found = extract_skills(p)
        # Check if the extracted skill is exactly the same as the language string (ignoring case)
        # or just if ANY skill is found, we exclude it?
        # If p is "C++ (Basic)", extract_skills finds "C++". It's a programming language, so exclude!
        if not skills_found:
            valid_parts.append(p)
    if valid_parts:
        clean_langs.append(", ".join(valid_parts))

print("Clean langs:", clean_langs)
