import re

with open('backend/analyzer.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Verify markers
start_marker = "def _is_edu_header_line(line: str) -> bool:"
end_marker = "def _group_project_lines(proj_lines):"

assert start_marker in content, "start_marker not found"
assert end_marker in content, "end_marker not found"

start_pos = content.find(start_marker)
end_pos = content.find(end_marker)

replacement = '''def _is_summary_or_non_edu(line: str) -> bool:
    """Detect sentences that describe summaries, objectives, skills, projects, declarations, or personal details."""
    l = line.lower().strip()
    if not l:
        return True
    
    summary_indicators = [
        "dedicated", "motivated", "seeking", "looking for", "aspiring", "passionate",
        "to work in", "to secure", "to obtain", "to serve", "eager to", "enthusiastic",
        "career objective", "professional summary", "about me", "profile summary",
        "results-driven", "hard-working", "strong foundation in", "proficient in",
        "hands-on experience", "proven track record", "self-motivated", "dynamic professional",
        "willing to work", "contribute to", "strive for", "aim to", "responsible for",
        "skilled in using", "experience in hands-on", "experience in", "worked on",
        "projects involving", "simulation and analysis", "circuit design", "power systems",
        "microcontrollers", "embedded systems", "software tools such as",
        "i hereby declare", "i certify that", "true and accurate", "to the best of my knowledge",
        "date of birth", "gender:", "father's name", "permanent address", "hobbies:",
        "languages known", "declaration", "place:", "date:"
    ]
    if any(ind in l for ind in summary_indicators):
        if not re.match(r'^(?:b\.?e\.?|b\.?tech|bachelor|master|m\.?tech|diploma|sslc|puc)\b', l):
            return True
        if len(l.split()) > 7:
            return True

    # Coursework or project lines
    if re.match(r'^(?:relevant\s+)?(?:courses|coursework|subjects|electives|modules)[\s:-]', l):
        return True
    if re.match(r'^(?:projects?|key\s+projects?|responsibilities|achievements?)[\s:-]', l):
        return True
    if re.match(r'^(?:skills?|technical\s+skills?|tools?)[\s:-]', l):
        return True
        
    return False


def _is_edu_header_line(line: str) -> bool:
    # A line with a graduation year, percentage, or CGPA is NEVER a table header!
    if re.search(r'\\b(19|20)\\d{2}\\b', line) or '%' in line or re.search(r'\\b(?:cgpa|gpa)[\\s:-]*\\d\\b', line, re.IGNORECASE):
        return False
        
    l = line.lower().strip()
    l = re.sub(r'^[|\\s\\-#*:]+', '', l)
    l = re.sub(r'[|\\s\\-#*:]+$', '', l)
    
    header_kws = [
        "institution", "university", "college", "school", "passing", 
        "cgpa", "percentile", "percentage", "marks", "grade", "degree", 
        "course", "qualification", "board", "stream", "specialization", 
        "duration", "batch", "score"
    ]
    kw_hits = sum(1 for kw in header_kws if kw in l)
    
    if ('|' in line or '\\t' in line) and kw_hits >= 2:
        return True
    return kw_hits >= 3 or ("degree" in l and "institution" in l) or ("course" in l and "college" in l) or ("institution" in l and "passing" in l)


DEGREE_PATTERNS = [
    # Doctorates
    r'\\b(?:ph\\.?d|doctorate|doctor\\s+of\\s+(?:philosophy|science)|d\\.phil)\\b',
    # Masters
    r'\\b(?:m\\.?tech|m\\.?e\\.?|(?<![a-z]\\.)m\\.s\\.|(?<![a-z]\\.)ms\\b|m\\.?sc|mca|mba|m\\.?com|m\\.?a\\.|m\\.?des|pg\\s+diploma|post\\s+graduate\\s+diploma)\\b',
    r'\\b(?:master(?:\\\'?s)?\\s+of\\s+(?:technology|engineering|science|arts|commerce|business\\s+administration|computer\\s+applications|philosophy|design|architecture|pharmacy|education))\\b',
    r'\\bmaster(?:\\\'?s)?\\s+degree\\b',
    # Bachelors & Engineering
    r'\\b(?:b\\.?tech|b\\.?e\\.?|(?<![a-z]\\.)b\\.s\\.|(?<![a-z]\\.)bs\\b|b\\.?sc|bca|bba|b\\.?com|b\\.?a\\.|b\\.?des|b\\.?arch|mbbs)\\b',
    r'\\b(?:bachelor(?:\\\'?s)?\\s+of\\s+(?:technology|engineering|science|arts|commerce|business\\s+administration|computer\\s+applications|philosophy|design|architecture|pharmacy|education|laws))\\b',
    r'\\bbachelor(?:\\\'?s)?\\s+degree\\b',
    # Engineering branches without explicit B.E./B.Tech prefix
    r'\\b(?:computer\\s+science(?:\\s+(?:and|&)\\s+engineering)?|information\\s+(?:science|technology)(?:\\s+(?:and|&)\\s+engineering)?|electrical(?:\\s+(?:and|&)\\s+electronics)?(?:\\s+engineering)?|electronics(?:\\s+(?:and|&)\\s+communication)?(?:\\s+engineering)?|(?:mechanical|civil|chemical|biotechnology|aeronautical|automobile|aerospace|industrial|robotics|data\\s+science)\\s+engineering)\\b',
    # Diploma
    r'\\b(?:diploma(?:\\s+in\\s+[A-Za-z\\s&]+)?|polytechnic(?:\\s+diploma)?|advanced\\s+diploma)\\b',
    # Pre-University / 12th
    r'\\b(?:pre[- ]university(?:\\s+course)?|puc(?:\\s*-\\s*[a-z]+)?|higher\\s+secondary(?:\\s+education)?|senior\\s+secondary(?:\\s+education)?|intermediate(?:\\s*\\(?[a-z]+\\)?)?|12th(?:\\s+std|\\s+standard|\\s+grade)?|class\\s+(?:xii|12|12th)|hsc|plus\\s+two|\\+2)\\b',
    # Secondary / 10th
    r'\\b(?:secondary\\s+school\\s+leaving\\s+certificate|secondary\\s+education|secondary\\s+school|sslc|10th(?:\\s+std|\\s+standard|\\s+grade)?|class\\s+(?:x|10|10th)|matriculation|high\\s+school(?:\\s+certificate)?)\\b',
    # Associate
    r'\\b(?:associate(?:\\\'?s)?\\s+degree)\\b'
]

INST_PATTERNS = [
    r'\\b(?:college|pu\\s+college)\\b',
    r'(?<!pre[- ])\\buniversity\\b',
    r'\\b(?:institute|institution|academy|vidyalaya|polytechnic|campus|vtu|iit|nit|iisc|bits|mit)\\b',
    r'(?<!secondary\\s)(?<!senior\\s)(?<!higher\\s)\\bschool\\b',
    r'\\b(?:board|council|examination\\s+board)\\b'
]


def _is_degree_kw(text: str) -> bool:
    t = text.lower()
    for pat in DEGREE_PATTERNS:
        if re.search(pat, t):
            return True
    return False


def _is_inst_kw(text: str) -> bool:
    t = text.lower()
    if re.search(r'\\b(?:pre[- ]university\\s+course|secondary\\s+school\\s+leaving\\s+certificate|secondary\\s+school|secondary\\s+education|sslc|puc)\\b', t):
        if not re.search(r'\\b(?:pu\\s+college|high\\s+school|public\\s+school|grammar\\s+school|secondary\\s+school\\s+examination\\s+board)\\b', t):
            return False
    return any(re.search(pat, t) for pat in INST_PATTERNS)


def _clean_field(text: str) -> str:
    if not text:
        return ""
    cleaned = re.sub(r'^[\\s\\-_–—•·▪►|:,;~"\\\'*#\\ufffd]+', '', text)
    cleaned = re.sub(r'[\\s\\-_–—•·▪►|:,;~"\\\'*#\\ufffd]+$', '', cleaned)
    cleaned = re.sub(r'\\s+', ' ', cleaned)
    return cleaned.strip()


def _extract_year_field(text: str):
    """
    Extracts actual or explicitly expected passing year.
    Returns (year_str, remaining_text).
    Never invents or assumes graduation year without explicit text evidence.
    """
    # 1. Expected graduation: "Expected 2026", "2022 - 2026 (Expected)", "Expected: May 2025"
    m = re.search(r'(?:(?:19|20)\\d{2}\\s*[-–—]\\s*)?(?:(?:19|20)\\d{2})\\s*\\(?(?:Expected|Pursuing)\\)?', text, re.IGNORECASE)
    if m:
        yr = _clean_field(m.group(0))
        rem = text.replace(m.group(0), ' ')
        return yr, rem

    m = re.search(r'(?:Expected|Graduating|Graduation)[\\s:-]*(?:[A-Za-z]+\\s+)?\\b((?:19|20)\\d{2})\\b', text, re.IGNORECASE)
    if m:
        yr = f"{m.group(1)} (Expected)"
        rem = text.replace(m.group(0), ' ')
        return yr, rem

    # 2. Passing year explicit: "Passing Year: 2024", "Year of Passing: 2022", "Passed in 2021", "Batch: 2020 - 2024"
    m = re.search(r'(?:Passing\\s+Year|Year\\s+of\\s+Passing|Graduated|Batch|Passed\\s+in)[\\s:-]*(?:[A-Za-z]+\\s+)?\\b((?:19|20)\\d{2}(?:\\s*[-–—]\\s*(?:19|20)\\d{2})?)\\b', text, re.IGNORECASE)
    if m:
        yr = _clean_field(m.group(1))
        rem = text.replace(m.group(0), ' ')
        return yr, rem

    # 3. Year range: "2020 - 2024" or "August 2020 - May 2024"
    m = re.search(r'\\b(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\\s,.]*)?((?:19|20)\\d{2})\\s*[-–—]\\s*(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\\s,.]*)?((?:19|20)\\d{2})\\b', text, re.IGNORECASE)
    if m:
        yr = f"{m.group(1)} – {m.group(2)}"
        rem = text.replace(m.group(0), ' ')
        return yr, rem

    # 4. Ongoing without expected year: "2022 - Present", "2021 - Ongoing"
    m = re.search(r'(?:[A-Za-z]+\\s+)?\\b((?:19|20)\\d{2})\\b\\s*[-–—]\\s*(?:Present|Ongoing|Current)\\b', text, re.IGNORECASE)
    if m:
        yr = "—"
        rem = text.replace(m.group(0), ' ')
        return yr, rem

    # 5. Standalone year: "2024", "2021"
    m = re.search(r'\\b(19\\d{2}|20\\d{2})\\b', text)
    if m:
        yr = m.group(1)
        rem = text.replace(m.group(0), ' ')
        return yr, rem

    return "", text


def _extract_grade_field(text: str):
    """
    Extracts percentage, CGPA, GPA, or grade.
    Returns (grade_str, remaining_text).
    Never converts CGPA to percentage or invents values.
    """
    # 1. CGPA: "CGPA: 8.8", "with a CGPA of 8.4", "8.8 CGPA", "CGPA 7.75 / 10"
    m = re.search(r'\\b(?:with\\s+a\\s+)?CGPA(?:\\s+of)?[\\s:-]*([0-9]+(?:\\.[0-9]+)?)(?:\\s*/\\s*(?:10(?:\\.0+)?|4(?:\\.0+)?|100))?\\b', text, re.IGNORECASE)
    if m:
        score = m.group(1)
        rem = text.replace(m.group(0), ' ')
        return f"CGPA: {score}", rem
        
    m = re.search(r'\\b([0-9]+(?:\\.[0-9]+)?)\\s*CGPA\\b', text, re.IGNORECASE)
    if m:
        rem = text.replace(m.group(0), ' ')
        return f"CGPA: {m.group(1)}", rem

    # 2. GPA out of 4: "GPA: 3.8 / 4.0", "3.8 / 4.0 GPA", "3.85 / 4.0"
    m = re.search(r'\\b(?:GPA[\\s:-]*)?([0-9]+(?:\\.[0-9]+)?)\\s*/\\s*4(?:\\.0+)?(?:\\s*GPA)?\\b', text, re.IGNORECASE)
    if m:
        rem = text.replace(m.group(0), ' ')
        return f"{m.group(1)} / 4.0 GPA", rem

    # 3. Ratio out of 10: "7.75 / 10", "8.8 / 10"
    m = re.search(r'\\b([0-9]+(?:\\.[0-9]+)?)\\s*/\\s*10(?:\\.0+)?\\b', text)
    if m:
        rem = text.replace(m.group(0), ' ')
        return f"CGPA: {m.group(1)}", rem

    # 4. Percentage: "Percentage: 84.96%", "scoring 91.5%", "84.96%", "90.72%"
    m = re.search(r'(?:Percentage[\\s:-]*|scoring[\\s:-]*|with[\\s:-]*)?([0-9]{1,3}(?:\\.[0-9]+)?)\\s*%', text, re.IGNORECASE)
    if m:
        rem = text.replace(m.group(0), ' ')
        return f"{m.group(1)}%", rem

    # 5. Percentile: "95.2 percentile"
    m = re.search(r'([0-9]{1,3}(?:\\.[0-9]+)?)\\s*(?:percentile|Percentile)\\b', text)
    if m:
        rem = text.replace(m.group(0), ' ')
        return f"{m.group(1)} Percentile", rem

    return "", text


def _format_degree_name(degree: str) -> str:
    d = _clean_field(degree)
    if not d:
        return ""
    d = re.sub(r'^(?:Degree|Course|Qualification|Exam|Examination)[\\s:-]+', '', d, flags=re.IGNORECASE)
    d = re.sub(r'[,;\\s]*(?:percentage|cgpa|score)[\\s:-]*[0-9]+(?:\\.[0-9]+)?%?.*$', '', d, flags=re.IGNORECASE)
    d = re.sub(r'[,;\\s]*\\b(19|20)\\d{2}\\b.*$', '', d)
    d = _clean_field(d)
    low = d.lower()
    
    # 10th / SSLC normalization
    if any(k in low for k in ['secondary education', 'secondary school', 'sslc', '10th', 'class 10', 'class x', 'matriculation', '10th standard', '10th std']):
        return "Secondary Education (SSLC)"
    if low in ['10th std / sslc', '10th std', '10th sslc', '10th standard / sslc', '10th std/sslc', 'class x (sslc)', 'class 10 (sslc)', 'secondary school (sslc)']:
        return "Class X (10th STD / SSLC)"
        
    # 12th / PUC normalization
    if any(k in low for k in ['pre-university', 'pre university', 'puc', 'pre-university course', 'pre university course']):
        return "Pre-University (PUC)"
    if any(k in low for k in ['higher secondary', '12th', 'class 12', 'class xii', 'hsc', 'plus two', '+2', 'senior secondary']):
        return "Higher Secondary (Class XII)"
    if 'intermediate' in low:
        return "Intermediate (Class XII)"

    # Engineering branches without B.E. / B.Tech prefix
    if re.search(r'\\bengineering\\b', low) and not any(k in low for k in ['b.e', 'b.tech', 'bachelor', 'master', 'm.tech', 'diploma']):
        return f"B.E. in {d}"

    return d


def _clean_inst_name(inst: str) -> str:
    cleaned = _clean_field(inst)
    if not cleaned:
        return ""
    cleaned = re.sub(r'^(?:Institution|Institute|University|College|School|Name\\s+of\\s+(?:the\\s+)?(?:Institution|College|School|University))[\\s]*[:\\-]\\s*', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'[,;\\s]*(?:emphasizing|focusing|specializing|with)\\s+core\\s+subjects\\s+.*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'[,;\\s]*(?:emphasizing|focusing|specializing|with)\\s+subjects\\s+.*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'[,;\\s]*core\\s+subjects\\s+.*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'[,;\\s]*such\\s+as\\s+.*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'[,;\\s]*completed\\s+.*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'[,;\\s]*(?:percentage|cgpa|score)[\\s:-]*[0-9]+(?:\\.[0-9]+)?%?.*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'[,;\\s]*\\b(19|20)\\d{2}\\b.*$', '', cleaned)
    cleaned = re.sub(r'\\s+\\b(?:in|scoring|with|from|at)\\s*$', '', cleaned, flags=re.IGNORECASE).strip()
    parts = [_clean_field(p) for p in re.split(r'[,|]', cleaned) if _clean_field(p)]
    clean_parts = [p for p in parts if p.lower() not in ['state', 'general', 'na', 'n/a', '-']]
    if clean_parts:
        return ", ".join(clean_parts)
    return cleaned


def _parse_single_line_qual(line: str):
    """
    Parses a self-contained single line or sentence describing a qualification:
    e.g. 'Completed Bachelor of Technology in Computer Science from National Institute of Technology Karnataka, Surathkal in 2023 with a CGPA of 8.4.'
    """
    text = line
    grade, text = _extract_grade_field(text)
    year, text = _extract_year_field(text)
    text = re.sub(r'^(?:Completed|Graduated|Pursuing|Enrolled\\s+in|Holds\\s+a)\\s+', '', text, flags=re.IGNORECASE)
    
    degree = ""
    inst = ""
    
    for pat in DEGREE_PATTERNS:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            d_start, d_end = m.start(), m.end()
            rest = text[d_end:]
            spec_match = re.search(r'^(?:\\s+in\\s+([A-Za-z\\s&]+?))(?:\\s+(?:from|at|,|\\.|$))', rest, re.IGNORECASE)
            if spec_match:
                spec = spec_match.group(1).strip()
                degree = f"{text[d_start:d_end]} in {spec}"
                text = text[:d_start] + " " + rest[spec_match.end(1):]
            else:
                degree = text[d_start:d_end]
                text = text[:d_start] + " " + rest
            break

    inst_match = re.search(r'(?:from|at)\\s+([A-Za-z0-9\\s,\\.\\\'\\-]+?(?:University|College|Institute|School|Academy|Polytechnic|Vidyalaya)[A-Za-z0-9\\s,\\.\\\'\\-]*)', text, re.IGNORECASE)
    if inst_match:
        inst = inst_match.group(1).strip(' ,.')
    else:
        parts = [_clean_field(p) for p in re.split(r'[,|]', text) if _clean_field(p)]
        inst_parts = [p for p in parts if _is_inst_kw(p)]
        if inst_parts:
            inst = ", ".join(inst_parts)

    degree = _format_degree_name(degree)
    inst = _clean_inst_name(inst)

    if degree or inst:
        return [degree or "—", inst or "—", year or "—", grade or "—"]
    return None


def _get_parsed_education_rows(edu_lines):
    """
    Universal dynamic education extraction pipeline.
    Works for ALL resume formats:
    - Tabular (pipe / tab / dash / space delimited)
    - Multi-line blocks
    - Paragraphs
    - Bullet points
    Extracts strictly from current candidate's resume; never hard-codes or invents details.
    """
    if not edu_lines:
        return []

    # Step 1: Combine fragmented lines (e.g. lines starting with 'and' or continuation of clauses)
    combined = []
    for line in edu_lines:
        l_str = _clean_field(line)
        if not l_str or _is_edu_header_line(l_str):
            continue
        if combined:
            prev = combined[-1]
            if (l_str.lower().startswith(('and ', 'or ', '& ', 'with ')) or 
                prev.lower().endswith(('such as', 'such as:', 'and', 'with', 'in', 'from', 'of', 'for', 'at', ',')) or
                (not l_str[0].isupper() and not _is_degree_kw(l_str) and not _is_inst_kw(l_str))):
                combined[-1] = prev + " " + l_str
                continue
        combined.append(l_str)

    if not combined:
        return []

    # Step 2: Process lines into structured qualification records
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
        # Delimited table row
        if '|' in line or '\\t' in line:
            flush_current()
            parts = [_clean_field(p) for p in re.split(r'[|\\t]', line) if _clean_field(p)]
            if any('degree' in p.lower() or 'course' in p.lower() for p in parts) and any('institution' in p.lower() or 'university' in p.lower() for p in parts):
                continue
            deg, inst, yr, gr = "", "", "", ""
            for p in parts:
                y_val, _ = _extract_year_field(p)
                g_val, _ = _extract_grade_field(p)
                if y_val and not yr: yr = y_val; continue
                if g_val and not gr: gr = g_val; continue
                if _is_degree_kw(p) and not deg: deg = p; continue
                if _is_inst_kw(p) and not inst: inst = p; continue
                if not inst: inst = p
            if deg or inst or yr or gr:
                records.append([_format_degree_name(deg) or "—", _clean_inst_name(inst) or "—", yr or "—", gr or "—"])
            continue

        y_val, y_rem = _extract_year_field(line)
        g_val, g_rem = _extract_grade_field(line)

        # Check if line is purely candidate summary, skills, or project description
        if _is_summary_or_non_edu(line):
            if g_val and not current['grade']:
                current['grade'] = g_val
            if y_val and not current['year']:
                current['year'] = y_val
            continue

        # Check if line has both degree and institution
        if _is_degree_kw(line) and _is_inst_kw(line):
            single = _parse_single_line_qual(line)
            if single and (single[0] != "—" and single[1] != "—"):
                if current['degree'] or current['inst']:
                    flush_current()
                current['degree'] = single[0]
                current['inst'] = single[1]
                if single[2] != "—" and not current['year']: current['year'] = single[2]
                if single[3] != "—" and not current['grade']: current['grade'] = single[3]
                if y_val and not current['year']: current['year'] = y_val
                if g_val and not current['grade']: current['grade'] = g_val
                continue

        has_deg = _is_degree_kw(line)
        has_inst = _is_inst_kw(line)

        if has_deg:
            if current['degree']:
                flush_current()
            
            parts = [_clean_field(p) for p in re.split(r'[,|–—]', line) if _clean_field(p)]
            if len(parts) > 1 and _is_degree_kw(parts[0]):
                current['degree'] = parts[0]
                current['inst'] = ", ".join(parts[1:])
            else:
                current['degree'] = line

            if y_val and not current['year']: current['year'] = y_val
            if g_val and not current['grade']: current['grade'] = g_val
            continue

        if has_inst:
            if not current['inst']:
                current['inst'] = line
            else:
                if line.lower() not in current['inst'].lower():
                    current['inst'] += " " + line

            if y_val and not current['year']: current['year'] = y_val
            if g_val and not current['grade']: current['grade'] = g_val
            continue

        # Residual text
        if y_val and not current['year']:
            current['year'] = y_val
        if g_val and not current['grade']:
            current['grade'] = g_val

        rem_str = _clean_field(y_rem.replace(g_val, '')) if y_val else _clean_field(g_rem)
        if rem_str and len(rem_str) < 30 and not _is_summary_or_non_edu(rem_str):
            if current['inst'] and rem_str.lower() not in current['inst'].lower():
                current['inst'] += ", " + rem_str
            elif not current['inst'] and not current['degree']:
                current['inst'] = rem_str

    flush_current()

    # Step 3: Deduplicate & merge records of same qualification
    merged = []
    for rec in records:
        deg, inst, yr, gr = rec
        match_idx = -1
        for idx, m in enumerate(merged):
            if deg != "—" and m[0] == deg:
                match_idx = idx
                break
            if "sslc" in deg.lower() and "sslc" in m[0].lower():
                match_idx = idx
                break
            if "puc" in deg.lower() and "puc" in m[0].lower():
                match_idx = idx
                break

        if match_idx >= 0:
            m = merged[match_idx]
            m_deg = m[0] if m[0] != "—" else deg
            m_inst = m[1] if (m[1] != "—" and len(m[1]) >= len(inst)) else (inst if inst != "—" else m[1])
            m_yr = m[2] if m[2] != "—" else yr
            m_gr = m[3] if m[3] != "—" else gr
            merged[match_idx] = [m_deg, m_inst, m_yr, m_gr]
        else:
            merged.append(rec)

    final_records = []
    for r in merged:
        if r[0] == "—" and r[1] == "—":
            continue
        final_records.append(r)

    return final_records\n\n\n'''

new_content = content[:start_pos] + replacement + content[end_pos:]

with open('backend/analyzer.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print('Updated analyzer.py successfully!')
