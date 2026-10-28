import re

DEGREE_PATTERNS = [
    r'\b(?:ph\.?d|doctorate|doctor\s+of\s+(?:philosophy|science)|d\.phil)\b',
    r'\b(?:m\.?tech|m\.?e\.?|(?<![a-z]\.)m\.s\.|(?<![a-z]\.)ms\b|m\.?sc|mca|mba|m\.?com|m\.?a\.|m\.?des|pg\s+diploma|post\s+graduate\s+diploma)\b',
    r'\b(?:master(?:\'?s)?\s+of\s+(?:technology|engineering|science|arts|commerce|business\s+administration|computer\s+applications|philosophy|design|architecture|pharmacy|education))\b',
    r'\bmaster(?:\'?s)?\s+degree\b',
    r'\b(?:b\.?tech|b\.?e\.?|(?<![a-z]\.)b\.s\.|(?<![a-z]\.)bs\b|b\.?sc|bca|bba|b\.?com|b\.?a\.|b\.?des|b\.?arch|mbbs)\b',
    r'\b(?:bachelor(?:\'?s)?\s+of\s+(?:technology|engineering|science|arts|commerce|business\s+administration|computer\s+applications|philosophy|design|architecture|pharmacy|education|laws))\b',
    r'\bbachelor(?:\'?s)?\s+degree\b',
    r'\b(?:computer\s+science(?:\s+(?:and|&)\s+engineering)?|information\s+(?:science|technology)(?:\s+(?:and|&)\s+engineering)?|electrical(?:\s+(?:and|&)\s+electronics)?(?:\s+engineering)?|electronics(?:\s+(?:and|&)\s+communication)?(?:\s+engineering)?|(?:mechanical|civil|chemical|biotechnology|aeronautical|automobile|aerospace|industrial|robotics|data\s+science)\s+engineering)\b',
    r'\b(?:diploma(?:\s+in\s+[A-Za-z\s&]+)?|polytechnic(?:\s+diploma)?|advanced\s+diploma)\b',
    r'\b(?:pre[- ]university(?:\s+course)?|puc(?:\s*-\s*[a-z]+)?|higher\s+secondary(?:\s+education)?|senior\s+secondary(?:\s+education)?|intermediate(?:\s*\(?[a-z]+\)?)?|12th(?:\s+std|\s+standard|\s+grade)?|class\s+(?:xii|12|12th)|hsc|plus\s+two|\+2)\b',
    r'\b(?:secondary\s+school\s+leaving\s+certificate|secondary\s+education|secondary\s+school|sslc|10th(?:\s+std|\s+standard|\s+grade)?|class\s+(?:x|10|10th)|matriculation|high\s+school\s+(?:certificate|diploma))\b',
    r'\b(?:associate(?:\'?s)?\s+degree)\b'
]

INST_PATTERNS = [
    r'\b(?:college|pu\s+college)\b',
    r'(?<!pre[- ])\buniversity\b',
    r'\b(?:institute|institution|academy|vidyalaya|polytechnic|campus|vtu|iit|nit|iisc|bits|mit)\b',
    r'(?<!secondary\s)(?<!senior\s)(?<!higher\s)\bschool\b',
    r'\b(?:board|council|examination\s+board)\b'
]

def _clean_field(text: str) -> str:
    if not text: return ""
    cleaned = re.sub(r'^[\s\-_–—•·▪►|:,;~"\'*#\ufffd]+', '', text)
    cleaned = re.sub(r'[\s\-_–—•·▪►|:,;~"\'*#\ufffd]+$', '', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned.strip()

def _is_degree_kw(text: str) -> bool:
    t = text.lower()
    return any(re.search(pat, t) for pat in DEGREE_PATTERNS)

def _is_inst_kw(text: str) -> bool:
    t = text.lower()
    if re.search(r'\b(?:pre[- ]university\s+course|secondary\s+school\s+leaving\s+certificate|secondary\s+school|secondary\s+education|sslc|puc)\b', t):
        if not re.search(r'\b(?:pu\s+college|high\s+school|public\s+school|grammar\s+school|secondary\s+school\s+examination\s+board)\b', t):
            return False
    return any(re.search(pat, t) for pat in INST_PATTERNS)

def _extract_year_field(text: str):
    m = re.search(r'(?:(?:19|20)\d{2}\s*[-–—]\s*)?(?:(?:19|20)\d{2})\s*\(?(?:Expected|Pursuing)\)?', text, re.IGNORECASE)
    if m: return _clean_field(m.group(0)), text.replace(m.group(0), ' ')
    m = re.search(r'(?:Expected|Graduating|Graduation)[\s:-]*(?:[A-Za-z]+\s+)?\b((?:19|20)\d{2})\b', text, re.IGNORECASE)
    if m: return f"{m.group(1)} (Expected)", text.replace(m.group(0), ' ')
    m = re.search(r'(?:Passing\s+Year|Year\s+of\s+Passing|Graduated|Batch|Passed\s+in)[\s:-]*(?:[A-Za-z]+\s+)?\b((?:19|20)\d{2}(?:\s*[-–—]\s*(?:19|20)\d{2})?)\b', text, re.IGNORECASE)
    if m: return _clean_field(m.group(1)), text.replace(m.group(0), ' ')
    m = re.search(r'\b(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s,.]*)?((?:19|20)\d{2})\s*[-–—]\s*(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s,.]*)?((?:19|20)\d{2})\b', text, re.IGNORECASE)
    if m: return f"{m.group(1)} – {m.group(2)}", text.replace(m.group(0), ' ')
    m = re.search(r'\b(19\d{2}|20\d{2})\b', text)
    if m: return m.group(1), text.replace(m.group(0), ' ')
    return "", text

def _extract_grade_field(text: str):
    m = re.search(r'\b(?:with\s+a\s+)?CGPA(?:\s+of)?[\s:-]*([0-9]+(?:\.[0-9]+)?)(?:\s*/\s*(?:10(?:\.0+)?|4(?:\.0+)?|100))?\b', text, re.IGNORECASE)
    if m: return f"CGPA: {m.group(1)}", text.replace(m.group(0), ' ')
    m = re.search(r'\b([0-9]+(?:\.[0-9]+)?)\s*CGPA\b', text, re.IGNORECASE)
    if m: return f"CGPA: {m.group(1)}", text.replace(m.group(0), ' ')
    m = re.search(r'\b([0-9]+(?:\.[0-9]+)?)\s*/\s*10(?:\.0+)?\b', text)
    if m: return f"CGPA: {m.group(1)}", text.replace(m.group(0), ' ')
    m = re.search(r'(?:Percentage[\s:-]*|scoring[\s:-]*|with[\s:-]*)?([0-9]{1,3}(?:\.[0-9]+)?)\s*%', text, re.IGNORECASE)
    if m: return f"{m.group(1)}%", text.replace(m.group(0), ' ')
    return "", text

def _format_degree_name(degree: str) -> str:
    d = _clean_field(degree)
    if not d: return ""
    d = re.sub(r'^(?:Degree|Course|Qualification|Exam|Examination)[\s:-]+', '', d, flags=re.IGNORECASE)
    d = re.sub(r'^(?:percentage|cgpa|score)[\s:-]*[0-9]+(?:\.[0-9]+)?%?[\s,;:-]*', '', d, flags=re.IGNORECASE)
    d = re.sub(r'[,;\s]*(?:percentage|cgpa|score)[\s:-]*[0-9]+(?:\.[0-9]+)?%?.*$', '', d, flags=re.IGNORECASE)
    d = re.sub(r'[,;\s]*\b(19|20)\d{2}\b.*$', '', d)
    d = _clean_field(d)
    low = d.lower()

    # 12th / PUC normalization
    if any(k in low for k in ['pre-university', 'pre university', 'puc', 'pre-university course', 'pre university course']):
        return "Pre-University (PUC)"
    if re.search(r'\b(?:higher\s+secondary|12th|class\s+xii|class\s+12|hsc|plus\s+two|\+2|senior\s+secondary)\b', low):
        return "Higher Secondary (Class XII)"
    if 'intermediate' in low:
        return "Intermediate (Class XII)"

    # 10th / SSLC normalization
    if re.search(r'\b(?:secondary\s+education|secondary\s+school|sslc|10th|class\s+x|class\s+10|matriculation)\b', low):
        return "Secondary Education (SSLC)"

    # Engineering branches without B.E. / B.Tech prefix
    if re.search(r'\bengineering\b', low) and not any(k in low for k in ['b.e', 'b.tech', 'bachelor', 'master', 'm.tech', 'diploma']):
        return f"B.E. in {d}"

    return d

def _clean_inst_name(inst: str) -> str:
    cleaned = _clean_field(inst)
    if not cleaned: return ""
    cleaned = re.sub(r'^(?:Institution|Institute|University|College|School|Name\s+of\s+(?:the\s+)?(?:Institution|College|School|University))[\s]*[:\-]\s*', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'[,;\s]*(?:emphasizing|focusing|specializing|with)\s+core\s+subjects\s+.*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'[,;\s]*(?:emphasizing|focusing|specializing|with)\s+subjects\s+.*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'[,;\s]*core\s+subjects\s+.*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'[,;\s]*such\s+as\s+.*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'[,;\s]*completed\s+.*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'[,;\s]*(?:percentage|cgpa|score)[\s:-]*[0-9]+(?:\.[0-9]+)?%?.*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'[,;\s]*\b(19|20)\d{2}\b.*$', '', cleaned)
    cleaned = re.sub(r'\s+\b(?:in|scoring|with|from|at)\s*$', '', cleaned, flags=re.IGNORECASE).strip()
    parts = [_clean_field(p) for p in re.split(r'[,|]', cleaned) if _clean_field(p)]
    clean_parts = [p for p in parts if p.lower() not in ['state', 'general', 'na', 'n/a', '-']]
    if clean_parts: return ", ".join(clean_parts)
    return cleaned

def parse_edu(lines):
    combined = []
    for line in lines:
        l_str = _clean_field(line)
        if not l_str: continue
        if combined:
            prev = combined[-1]
            if (l_str.lower().startswith(('and ', 'or ', '& ', 'with ')) or 
                prev.lower().endswith(('such as', 'such as:', 'and', 'with', 'in', 'from', 'of', 'for', 'at', ',')) or
                (not l_str[0].isupper() and not _is_degree_kw(l_str) and not _is_inst_kw(l_str))):
                combined[-1] = prev + " " + l_str
                continue
        combined.append(l_str)

    records = []
    current = {'degree': '', 'inst': '', 'year': '', 'grade': ''}

    def flush_current():
        nonlocal current
        deg = _format_degree_name(current['degree'])
        inst = _clean_inst_name(current['inst'])
        yr = current['year']
        gr = current['grade']
        if deg or inst:
            records.append([deg or "—", inst or "—", yr or "—", gr or "—"])
        current = {'degree': '', 'inst': '', 'year': '', 'grade': ''}

    for line in combined:
        y_val, y_rem = _extract_year_field(line)
        g_val, g_rem = _extract_grade_field(line)

        # Check for both degree and institution in one line
        has_deg = _is_degree_kw(line)
        has_inst = _is_inst_kw(line)

        if has_deg and has_inst:
            # Single line qualification
            if current['degree'] or current['inst']:
                flush_current()
            parts = [_clean_field(p) for p in re.split(r'[,|–—]', line) if _clean_field(p)]
            deg_part, inst_part = "", ""
            for p in parts:
                if _is_degree_kw(p) and not deg_part: deg_part = p
                elif _is_inst_kw(p) and not inst_part: inst_part = p
            current['degree'] = deg_part or line
            current['inst'] = inst_part
            if y_val: current['year'] = y_val
            if g_val: current['grade'] = g_val
            flush_current()
            continue

        if has_deg:
            if current['degree']:
                flush_current()
            # Clean degree from any attached grade/year
            deg_clean = line
            if g_val: deg_clean = deg_clean.replace(g_val, ' ')
            if y_val: deg_clean = deg_clean.replace(y_val, ' ')
            deg_clean = re.sub(r'^(?:percentage|cgpa|score)[\s:-]*[0-9]+(?:\.[0-9]+)?%?[\s,;:-]*', '', deg_clean, flags=re.IGNORECASE)
            deg_clean = re.sub(r'[,;\s]*(?:percentage|cgpa|score)[\s:-]*[0-9]+(?:\.[0-9]+)?%?.*$', '', deg_clean, flags=re.IGNORECASE)
            current['degree'] = _clean_field(deg_clean)
            if y_val and not current['year']: current['year'] = y_val
            if g_val and not current['grade']: current['grade'] = g_val
            continue

        if has_inst:
            if current['inst']:
                # Already have institution. If we have degree or grade/year, this is next entry!
                if current['degree'] or current['year'] or current['grade']:
                    flush_current()
                    current['inst'] = line
                else:
                    if line.lower() not in current['inst'].lower():
                        current['inst'] += " " + line
            else:
                if current['degree'] and (current['year'] or current['grade']):
                    flush_current()
                current['inst'] = line

            if y_val and not current['year']: current['year'] = y_val
            if g_val and not current['grade']: current['grade'] = g_val
            continue

        # Line without degree or inst keyword: update year/grade or inst detail
        if y_val and not current['year']: current['year'] = y_val
        if g_val and not current['grade']: current['grade'] = g_val

    flush_current()
    return records

import fitz
for name in ['Resume 6.pdf', 'resume vinay.pdf', 'Resume 5.pdf']:
    doc = fitz.open(f'C:/Users/nandi/Desktop/Resumes/{name}')
    text = '\n'.join(p.get_text() for p in doc)
    from backend.analyzer import _parse_resume_sections
    sec = _parse_resume_sections(text)
    rows = parse_edu(sec.get('Education', []))
    print('*** ' + name + ' ***')
    for r in rows:
        print(' ', r)
