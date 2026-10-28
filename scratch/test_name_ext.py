import re

header_lines = ['### RESUME', '| | |', '| :--- | :--- |', '| **NAME:** | Basamma |', '| **EMAIL ID:** | Basammarajapur82@gmail.com |', '| **MOBILE NO.** | 7676136892 |']

def _extract_name(resume_text: str, header_lines: list) -> str:
    # 1. Search for explicit "NAME:" or "Name:" pattern in the top 20 lines
    for line in header_lines + [l.strip() for l in resume_text.split('\n')[:20]]:
        m = re.search(r'(?:\*{0,2}NAME\*{0,2}[\s:-]+|\bName\s*:\s*)([A-Za-z][A-Za-z\s.\'\-]{1,40})', line, re.IGNORECASE)
        if m:
            cand = m.group(1).strip(' |*\t\r\n')
            if cand.lower() not in ['resume', 'curriculum vitae', 'cv', 'profile', 'summary', 'objective']:
                return cand.strip()
                
    # 2. Look for first line in header that isn't a title/keyword
    for line in header_lines:
        clean = re.sub(r'^[#*|\s\-–—]+', '', line).strip()
        clean = re.sub(r'[#*|\s\-–—]+$', '', clean).strip()
        if not clean:
            continue
        low = clean.lower()
        if any(kw in low for kw in ['resume', 'curriculum vitae', 'cv', 'page', 'email', 'phone', 'mobile', 'address', 'contact', 'profile', 'summary', 'objective']):
            continue
        if 2 <= len(clean) <= 40 and re.match(r'^[A-Za-z][A-Za-z\s.\'\-]+$', clean):
            return clean
            
    if header_lines:
        cand = re.sub(r'^[#*|\s\-–—]+', '', header_lines[0]).strip()
        if cand.lower() not in ['resume', 'curriculum vitae', 'cv']:
            return cand
    return "Candidate Name"

print("Extracted Name:", repr(_extract_name("", header_lines)))
